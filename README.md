# ClawCloud 自动保活脚本 (青龙面版适用)

专为 **青龙面板** 环境设计的 ClawCloud 自动登录保活脚本。

## ✨ 核心功能

*   **多账号支持**：支持配置无限个账号，顺序执行保活。
*   **Cookie 复用**：优先使用本地缓存 Cookie，减少登录频率，降低风控风险。
*   **自动 2FA 验证**：
    *   **强制密钥模式**：支持 TOTP (Authenticator) 两步验证，需配置 `totp_secret` 密钥，实现全自动无人值守登录。
    *   注：为保证稳定性，已移除交互式验证功能。
*   **多渠道通知**：
    *   **Telegram**: 支持发送文本汇总和异常截图。
    *   **微信**: 支持自定义 API (如 wxpush) 推送通知。
*   **智能代理 (国内环境优化)**：
    *   自动检测 `CLAW_PROXY` 或 `HTTP_PROXY` 环境变量。
    *   检测到代理时，自动配置浏览器和网络请求走代理，并自动处理 Docker 容器内的 `localhost` 连接问题，确保国内网络下稳定运行。
*   **环境适配**：针对 ARM64 (树莓派/M1) 和 AMD64 环境下的 Chromium/Chrome 路径进行了自动适配。

## 🛠️ 环境要求

*   **环境**: 青龙面板 (推荐 v2.10+)
*   **依赖**:
    *   Python 3.8+
    *   Chromium / Chrome 浏览器
    *   ChromeDriver
*   **Python 库** (青龙面板依赖管理 -> Python 中添加):
    ```logo
    selenium
    requests
    loguru
    pyotp
    ```
*   **系统包** (青龙面板依赖管理 -> Linux 中添加):
    ```bash
    chromium
    chromium-chromedriver
    ```
    *(注：部分镜像可能直接集成了 chrome，视具体环境而定)*

### 💻 SSH 手动安装依赖 (推荐)

如果您熟悉 SSH，可以直接进入容器安装，速度更快且更稳定。

1.  **进入青龙容器**
    ```bash
    docker exec -it qinglong bash
    # 注意: 'qinglong' 是您的容器名，如果不确定请使用 docker ps 查看
    ```

2.  **安装 Linux 系统依赖**
    ```bash
    apt update
    apt install -y chromium chromium-driver
    ```
    *(如果是 Debian/Ubuntu 环境，请使用 `apt-get install chromium-driver`)*

3.  **安装 Python 依赖**
    ```bash
    pip3 install selenium requests loguru pyotp
    ```

## ⚙️ 环境变量配置

请在青龙面板的「环境变量」中添加以下配置：

### 1. 账号配置 (必须)

| 变量名 | 描述 | 格式 |
| :--- | :--- | :--- |
| `CLAW_ACCOUNTS` | 账号列表 | `账号----密码----2FA密钥` |

*   **多账号**：用 `&` 符号连接。
*   **备注支持**：支持在账号后加 `#备注`，脚本会自动忽略。

**示例**：
```bash
# 单账号
user@gmail.com----password123----JBSWY3DPEHPK3PXP

# 多账号 (带备注)
user1@gmail.com#主号----pass1----SECRET1&user2@qq.com#小号----pass2----SECRET2
```

### 2. 代理配置 (国内用户推荐)

| 变量名 | 描述 | 示例 |
| :--- | :--- | :--- |
| `CLAW_PROXY` | 代理地址 | `http://192.168.1.5:7890` |
| `HTTP_PROXY` | 系统代理 (备选) | `http://192.168.1.5:7890` |

*   **作用**：启用后，浏览器登录 GitHub/ClawCloud 以及发送 Telegram 消息都会走此代理。
*   **无需配置**：如果你是国外 VPS，可不填。

### 3. 通知配置 (可选)

| 变量名 | 描述 | 说明 |
| :--- | :--- | :--- |
| `TG_BOT_TOKEN` | Telegram Bot Token | 机器人 Token |
| `TG_CHAT_ID` | Telegram Chat ID | 接收消息的用户 ID |
| `WECHAT_API_URL` | 微信推送 API | 自定义 GET/POST 接口地址 |
| `WECHAT_AUTH_TOKEN` | 微信推送 Token | 接口鉴权 Token |

## 🚀 运行说明

1.  将脚本 `clawcloud_arm64.py` 添加到青龙面板的脚本库或直接上传。
2.  添加定时任务：
    *   命令：`task clawcloud_auto_live.py`
    *   定时：`0 12 * * 5` (每周五自动运行一次)
3.  点击运行日志，查看执行情况。

## 📂 文件结构

*   `clawcloud_arm64.py`: 主脚本文件
*   `cookies_xxx.json`: 脚本自动生成的 Cookie 缓存文件 (自动生成，无需管理)
*   `*.png`: 运行过程中生成的临时截图 (脚本运行结束会自动清理)

## ⚠️ 常见问题

1.  **报错 `Network unreachable`**
    *   请检查是否配置了 `CLAW_PROXY`。国内网络直连 Google/GitHub/Telegram 通常不通。
2.  **报错 `WebDriverException: Session not created`**
    *   通常是 Chrome 和 ChromeDriver 版本不匹配，或未安装 Chromium。请检查青龙面板的 Linux 依赖是否安装了 `chromium` 和 `chromium-chromedriver`。
3.  **2FA 登录失败**
    *   请确保 `totp_secret` 是正确的 Base32 密钥字符串（通常是添加 Authenticator 时显示的密钥）。不要填 6 位动态码。

