//! 扩展自有 HTTP 访问协议。这里不承载 Peer HTTP delegation，也不验证外部协议凭证。

use std::collections::HashSet;

use base64::{Engine, engine::general_purpose::STANDARD};
use serde::{Deserialize, Deserializer, Serialize, Serializer, de};

use crate::Error;

pub const MAX_HTTP_FRAME_BYTES: usize = 64 * 1024 * 1024;
pub const MAX_HTTP_BODY_BYTES: usize = 45 * 1024 * 1024;
pub const MAX_HTTP_HEADER_BYTES: usize = 64 * 1024;

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HttpIngress {
    pub routes: Vec<HttpRoute>,
    #[serde(default)]
    pub peer_inbounds: Vec<PeerHttpInbound>,
}

impl HttpIngress {
    pub fn validate(&self) -> Result<(), Error> {
        if self.routes.is_empty() || self.routes.len() > 256 || self.peer_inbounds.len() > 256 {
            return invalid("HTTP ingress 必须声明 1..256 条路由，inbound 最多 256 条");
        }
        let mut routes = HashSet::new();
        for route in &self.routes {
            validate_http_method(&route.method)?;
            validate_http_path(&route.path)?;
            if !routes.insert((&route.method, &route.path, route.path_match)) {
                return invalid("HTTP method/path/match 不可重复");
            }
        }
        let mut capabilities = HashSet::new();
        for inbound in &self.peer_inbounds {
            if inbound.capability.is_empty()
                || inbound.capability.len() > 512
                || !capabilities.insert(&inbound.capability)
            {
                return invalid("Peer inbound capability 必须非空、有界且唯一");
            }
            if !self.routes.iter().any(|route| {
                route.method == inbound.method
                    && route.path == inbound.path
                    && route.path_match == HttpPathMatch::Exact
                    && route.auth == HttpAuth::Peer
            }) {
                return invalid("Peer inbound 必须精确引用一条 Peer 认证路由");
            }
        }
        Ok(())
    }

    /// Host 在发布前按已验证的 Extension Name 限定 mount，避免覆盖其他扩展或 Core。
    pub fn validate_mount(&self, extension_name: &str) -> Result<(), Error> {
        crate::validate_name(extension_name)?;
        self.validate()?;
        let (_, name) = extension_name.split_once('/').expect("validated name");
        let root = format!("/{name}");
        if self
            .routes
            .iter()
            .any(|route| !path_prefix(&root, &route.path))
        {
            return invalid("HTTP 路由只能位于 Extension name 的根路径内");
        }
        Ok(())
    }

    /// 输入为解码一次后的规范路径；Host 和插件不得再次百分号解码。
    pub fn admit(&self, method: &str, path: &str) -> Option<&HttpRoute> {
        if validate_http_method(method).is_err() || validate_http_path(path).is_err() {
            return None;
        }
        self.routes
            .iter()
            .filter(|route| route.method == method && route.matches(path))
            .max_by_key(|route| (route.path_match == HttpPathMatch::Exact, route.path.len()))
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HttpRoute {
    pub method: String,
    pub path: String,
    #[serde(default)]
    pub path_match: HttpPathMatch,
    #[serde(default)]
    pub auth: HttpAuth,
}

impl HttpRoute {
    fn matches(&self, path: &str) -> bool {
        match self.path_match {
            HttpPathMatch::Exact => self.path == path,
            HttpPathMatch::Prefix => path_prefix(&self.path, path),
        }
    }
}

#[derive(Clone, Copy, Debug, Default, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "snake_case")]
pub enum HttpPathMatch {
    #[default]
    Exact,
    Prefix,
}

#[derive(Clone, Copy, Debug, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum HttpAuth {
    /// Host 必须先验证 deployment Peer JWT，才可交给插件。
    #[default]
    Peer,
    /// Host 保留外部协议凭证，由插件完成认证；不会替换为 Peer JWT。
    Protocol,
    /// 作者显式公开的观察；不会得到其他 admission surface 的权限。
    Public,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PeerHttpInbound {
    pub capability: String,
    pub method: String,
    pub path: String,
}

/// 同名重复 header 保留顺序；value 为原始 bytes，不隐式转成 UTF-8。
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HttpHeader {
    pub name: String,
    pub value: Vec<u8>,
}

/// 标准 padded Base64 wire string；Rust 作者读写 decoded bytes。
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct HttpBody(pub Vec<u8>);

impl Serialize for HttpBody {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        if self.0.len() > MAX_HTTP_BODY_BYTES {
            return Err(serde::ser::Error::custom("HTTP body 超过 45 MiB"));
        }
        serializer.serialize_str(&STANDARD.encode(&self.0))
    }
}

impl<'de> Deserialize<'de> for HttpBody {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let encoded = String::deserialize(deserializer)?;
        if encoded.len() > MAX_HTTP_BODY_BYTES.div_ceil(3) * 4 {
            return Err(de::Error::custom("HTTP body 超过 45 MiB"));
        }
        let body = STANDARD.decode(encoded).map_err(de::Error::custom)?;
        if body.len() > MAX_HTTP_BODY_BYTES {
            return Err(de::Error::custom("HTTP body 超过 45 MiB"));
        }
        Ok(Self(body))
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HttpRequest {
    pub method: String,
    /// 解码一次的绝对路径，不含 query；拒绝 '%'，避免解码次数造成认证差异。
    pub path: String,
    /// 原始 query string，不含 '?'。
    #[serde(default)]
    pub query: String,
    #[serde(default)]
    pub headers: Vec<HttpHeader>,
    #[serde(default)]
    pub body: HttpBody,
}

impl HttpRequest {
    pub fn validate(&self) -> Result<(), Error> {
        validate_http_method(&self.method)?;
        validate_http_path(&self.path)?;
        if self.query.len() > MAX_HTTP_HEADER_BYTES
            || self.query.bytes().any(|byte| byte.is_ascii_control())
        {
            return invalid("HTTP query 无效或超限");
        }
        validate_message(&self.headers, &self.body)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HttpResponse {
    pub status: u16,
    #[serde(default)]
    pub headers: Vec<HttpHeader>,
    #[serde(default)]
    pub body: HttpBody,
}

impl HttpResponse {
    pub fn validate(&self) -> Result<(), Error> {
        if !(200..=599).contains(&self.status) {
            return invalid("HTTP 响应 status 必须为 200..599");
        }
        validate_message(&self.headers, &self.body)
    }
}

pub fn validate_http_method(method: &str) -> Result<(), Error> {
    if method.is_empty() || method.len() > 64 || !method.bytes().all(http_token) {
        return invalid("HTTP method 必须为有界 RFC token");
    }
    Ok(())
}

pub fn validate_http_path(path: &str) -> Result<(), Error> {
    if !path.starts_with('/')
        || path.len() > 8192
        || path.contains(['%', '?', '#', '\\'])
        || path.chars().any(char::is_control)
        || path
            .split('/')
            .skip(1)
            .any(|part| part == "." || part == "..")
        || path.contains("//")
    {
        return invalid("HTTP path 必须是无转义、无 dot segments 的规范绝对路径");
    }
    Ok(())
}

fn path_prefix(prefix: &str, path: &str) -> bool {
    path == prefix
        || path
            .strip_prefix(prefix.trim_end_matches('/'))
            .is_some_and(|rest| rest.starts_with('/'))
}

fn validate_message(headers: &[HttpHeader], body: &HttpBody) -> Result<(), Error> {
    if headers.len() > 256 || body.0.len() > MAX_HTTP_BODY_BYTES {
        return invalid("HTTP headers/body 超限");
    }
    let mut bytes = 0usize;
    for header in headers {
        bytes += header.name.len() + header.value.len();
        if header.name.is_empty()
            || !header
                .name
                .bytes()
                .all(|byte| http_token(byte) && !byte.is_ascii_uppercase())
            || header
                .value
                .iter()
                .any(|byte| (*byte < 0x20 && *byte != b'\t') || *byte == 0x7f)
            || bytes > MAX_HTTP_HEADER_BYTES
        {
            return invalid("HTTP header 必须为小写 token 和无换行的有界 bytes");
        }
    }
    Ok(())
}

fn http_token(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || b"!#$%&'*+-.^_`|~".contains(&byte)
}

fn invalid<T>(message: &str) -> Result<T, Error> {
    Err(Error::Protocol(message.into()))
}
