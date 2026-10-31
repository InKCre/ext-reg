---
'@inkcre/extension-runtime-client-web': patch
---

禁止重新激活已释放的模块句柄，防止新资源绕过后续幂等清理。
