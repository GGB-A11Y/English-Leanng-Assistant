# Resend 发信配置(腾讯云域名)

本项目用 [Resend](https://resend.com) 发送密码重置邮件。域名托管在腾讯云时,按本文档配置即可从测试模式切换到生产发信。

## 1. 测试模式(本地开发,无需域名)

1. 注册 Resend 账号 → API Keys → 创建密钥(测试模式密钥以 `re_` 开头)
2. 本地注入环境变量:

   ```bat
   setx RESEND_API_KEY "re_你的密钥"
   ```

3. `RESEND_FROM` 保持默认 `onboarding@resend.dev`(**测试模式只能发到 Resend 账号本人邮箱**,发到其他地址会被静默丢弃或报错)

## 2. 生产模式:验证域名

1. Resend 控制台 → **Domains** → **Add Domain** → 输入你的域名(推荐用子域名,如 `mail.example.com`,不影响主站解析)
2. Resend 会给出 3 组 DNS 记录(具体值以面板为准,通常为):
   - **SPF**:TXT 记录,host `@` 或子域名,值类似 `v=spf1 include:amazonses.com ~all`
   - **DKIM**:CNAME 记录,host 类似 `resend._domainkey.mail`,值类似 `resend.dkim.resend.com`(需两条,值末尾的数字不同)
   - **DMARC(可选)**:TXT 记录,host `_dmarc.mail`,值类似 `v=DMARC1; p=none;`
3. **腾讯云 DNS 控制台**([console.cloud.tencent.com/cns](https://console.cloud.tencent.com/cns))→ 我的域名 → 选择你的域名 → **解析** → 逐条「添加记录」:
   - 记录类型按 Resend 面板给的类型选择(TXT / CNAME)
   - 主机记录填面板给的 host(去掉你域名本身的后缀;面板显示 `xxx.mail.example.com` 就填 `xxx.mail`)
   - 记录值填面板给的 value
4. 回到 Resend 点 **Verify**(生效一般几分钟到几小时,取决于 TTL 与传播)
5. 验证通过后状态变为 **Verified**,即可正式发信

## 3. 应用配置

`.env`(非敏感配置)或环境变量:

```
RESEND_FROM=英语学习助手 <no-reply@mail.example.com>   # 用上一步验证过的域名
FRONTEND_URL=http://localhost:5173                      # 部署后改为 https://你的域名
```

密钥仍然只走环境变量(不落 .env 文件,与 LLM 密钥同一约定):

```bat
setx RESEND_API_KEY "re_你的密钥"        # 测试模式;生产建议换 live 密钥并在服务器上注入
```

重启后端后,重置密码邮件即从你的域名发出。前端部署到 `https://你的域名` 时,把 `FRONTEND_URL` 同步改为该地址(邮件里的重置链接才能用)。

## 4. 常见问题

| 现象 | 原因/处理 |
|---|---|
| 测试模式下发给其他邮箱收不到 | 测试模式仅允许发到 Resend 账号本人邮箱,完成第 2 节域名验证后再对外发 |
| 接口返回 503「邮件发送失败」 | 后端日志有具体原因;常见:RESEND_API_KEY 未注入 / 密钥无效 / RESEND_FROM 使用了未验证的域名 |
| Resend 面板一直未验证 | 检查腾讯云解析里的主机记录是否多写/少写了域名后缀;TTL 长时多等一会儿 |
| 收件箱进了垃圾邮件 | 补上 DMARC 记录;发信域名用独立子域名可降低对主域名的信誉影响 |
