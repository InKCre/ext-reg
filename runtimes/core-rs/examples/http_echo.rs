use async_trait::async_trait;
use inkcre_extension_sdk::{
    Capabilities, Descriptor, Extension, HttpAuth, HttpHeader, HttpIngress, HttpPathMatch,
    HttpRequest, HttpResponse, HttpRoute, PROTOCOL_VERSION, PeerHttpInbound, RpcError, SDK_VERSION,
    StartContext, serve,
};
use serde_json::{Value, json};

struct HttpEcho;

#[async_trait]
impl Extension for HttpEcho {
    fn descriptor(&self) -> Descriptor {
        Descriptor {
            name: "example/http-echo".into(),
            version: "0.1.0".parse().expect("static version"),
            sdk_version: SDK_VERSION.parse().expect("SDK version"),
            protocol_version: PROTOCOL_VERSION,
            config_schema: json!({"type":"object"}),
            methods: vec![],
            capabilities: Capabilities {
                http_ingress: Some(HttpIngress {
                    routes: vec![
                        HttpRoute {
                            method: "GET".into(),
                            path: "/http-echo/connection".into(),
                            path_match: HttpPathMatch::Exact,
                            auth: HttpAuth::Peer,
                        },
                        HttpRoute {
                            method: "PROPFIND".into(),
                            path: "/http-echo".into(),
                            path_match: HttpPathMatch::Prefix,
                            auth: HttpAuth::Protocol,
                        },
                    ],
                    peer_inbounds: vec![PeerHttpInbound {
                        capability: "http-echo.connection.v1".into(),
                        method: "GET".into(),
                        path: "/http-echo/connection".into(),
                    }],
                }),
                ..Default::default()
            },
        }
    }

    async fn start(&mut self, _: StartContext) -> Result<Value, RpcError> {
        Ok(json!({"started": true}))
    }

    async fn invoke(&mut self, _: &str, _: Value) -> Result<Value, RpcError> {
        Err(RpcError::new("unknown_method", "示例没有通用方法"))
    }

    async fn http_request(&mut self, request: HttpRequest) -> Result<HttpResponse, RpcError> {
        // 生产代码应从最新配置读取自己的协议凭证；这里使用仅用于显式验收的固定值。
        if request.method == "PROPFIND"
            && !request.headers.iter().any(|header| {
                header.name == "authorization" && header.value == b"Bearer acceptance"
            })
        {
            return Ok(HttpResponse {
                status: 401,
                headers: vec![],
                body: Default::default(),
            });
        }
        Ok(HttpResponse {
            status: 200,
            headers: vec![HttpHeader {
                name: "content-type".into(),
                value: b"application/octet-stream".to_vec(),
            }],
            body: request.body,
        })
    }

    async fn stop(&mut self) -> Result<(), RpcError> {
        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<(), inkcre_extension_sdk::Error> {
    serve(HttpEcho).await
}
