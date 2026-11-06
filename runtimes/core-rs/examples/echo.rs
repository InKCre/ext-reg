use async_trait::async_trait;
use inkcre_extension_sdk::{
    Descriptor, Extension, PROTOCOL_VERSION, RpcError, SDK_VERSION, StartContext, serve,
};
use serde_json::{Value, json};

#[derive(Default)]
struct Echo {
    peer_id: String,
}

#[async_trait]
impl Extension for Echo {
    fn descriptor(&self) -> Descriptor {
        Descriptor {
            name: "example/echo".into(),
            version: "0.1.0".parse().expect("static version"),
            sdk_version: SDK_VERSION.parse().expect("SDK version"),
            protocol_version: PROTOCOL_VERSION,
            config_schema: json!({"type":"object", "properties":{"prefix":{"type":"string"}}, "additionalProperties":false}),
            methods: vec!["echo".into()],
            capabilities: Default::default(),
        }
    }
    async fn start(&mut self, context: StartContext) -> Result<Value, RpcError> {
        self.peer_id = context.peer_id;
        eprintln!("example/echo 已启动");
        Ok(json!({"started":true}))
    }
    async fn invoke(&mut self, method: &str, params: Value) -> Result<Value, RpcError> {
        match method {
            "echo" => Ok(json!({"peer_id":self.peer_id,"echo":params})),
            _ => Err(RpcError::new("unknown_method", "方法不存在")),
        }
    }
    async fn stop(&mut self) -> Result<(), RpcError> {
        eprintln!("example/echo 已停止");
        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<(), inkcre_extension_sdk::Error> {
    serve(Echo::default()).await
}
