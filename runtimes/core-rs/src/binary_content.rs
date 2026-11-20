use base64::{Engine, engine::general_purpose::STANDARD};
use serde::{Deserialize, Deserializer, Serialize, Serializer, de, ser};

pub const MAX_BINARY_CONTENT_BYTES: usize = 32 * 1024 * 1024;

/// One base64-encoded binary value on a negotiated capability frame.
#[derive(Debug)]
pub struct BinaryContent(pub Vec<u8>);

impl Serialize for BinaryContent {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        if self.0.len() > MAX_BINARY_CONTENT_BYTES {
            return Err(ser::Error::custom("binary content exceeds byte limit"));
        }
        serializer.serialize_str(&STANDARD.encode(&self.0))
    }
}

impl<'de> Deserialize<'de> for BinaryContent {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let encoded = String::deserialize(deserializer)?;
        if encoded.len() > MAX_BINARY_CONTENT_BYTES.div_ceil(3) * 4 {
            return Err(de::Error::custom("binary content exceeds byte limit"));
        }
        let data = STANDARD.decode(encoded).map_err(de::Error::custom)?;
        if data.len() > MAX_BINARY_CONTENT_BYTES {
            return Err(de::Error::custom("binary content exceeds byte limit"));
        }
        Ok(Self(data))
    }
}
