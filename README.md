# TG 靓号订单管理机器人

基于 Python + aiogram 3 + SQLite 的 Telegram 话费/电费接单机器人，部署在 Oracle Cloud 永久免费 VPS 上。

## 功能清单

### 操作员功能
- **群内自然语言下单**：直接发 `手机号 运营商 金额 姓名`，支持一行多单批量
- **订单查询**：发 `本群订单` 看统计，发 `本群话费订单` 看明细（带完成按钮）
- **按钮完成订单**：点击订单消息下方「✅ 充值完成」按钮
- **部分充值回填**：`/recharge 手机号 金额`
- **撤单申请**：发 `撤单 手机号1 手机号2`，支持批量
- **模糊搜索**：`/search 手机号`

### 管理员功能
- `/addop TG_ID` 添加操作员
- `/delop TG_ID` 删除操作员
- `/listop` 列出全部操作员
- `/cancellist` 查看待审核撤单申请（带同意/拒绝按钮）
- `/cancelok 申请编号` 同意撤单
- `/del 手机号` 直接删除订单

### 其他
- 手机号地区自动识别（基于号段库）
- 未授权用户自动拦截
- 撤单审核通过后群内+私聊双通知
- 订单完成通知带「车队」用户名

---

## 一、创建 Telegram 机器人

1. 在 Telegram 搜索 **@BotFather**，发送 `/newbot`
2. 按提示设置机器人名称和用户名（用户名必须以 `bot` 结尾）
3. 创建成功后，BotFather 会给你一个 **HTTP API Token**，复制保存
4. 关闭隐私模式（必须，否则机器人读不到群消息）：
   - 发送 `/setprivacy` 给 @BotFather
   - 选择你的机器人
   - 选择 `Disable`
5. （可选）设置命令菜单：发送 `/setcommands`，粘贴：
   ```
   start - 查看菜单与授权状态
   help - 帮助
   recharge - 部分充值回填 手机号 金额
   search - 模糊搜索订单 手机号
   groupinfo - 查看群状态
   addop - 管理员：添加操作员 TG_ID
   delop - 管理员：删除操作员 TG_ID
   listop - 管理员：列出操作员
   cancellist - 管理员：查看撤单申请
   cancelok - 管理员：同意撤单 申请编号
   del - 管理员：删除订单 手机号
   ```

## 二、获取你的 TG ID

1. 把机器人代码跑起来后，私聊机器人发送 `/start`
2. 机器人会显示「您的 ID：xxxxxxxxxx」
3. 这个数字就是你的 TG ID，填到 `SUPER_ADMIN_ID`

## 三、Oracle Cloud 免费 VPS 部署

### 3.1 注册 Oracle Cloud

1. 访问 https://www.oracle.com/cloud/free/ 注册账号
2. 需要信用卡验证（不会扣费，仅验证）
3. 注册时选择就近区域（如日本东京、韩国首尔）

### 3.2 创建虚拟机

1. 登录 Oracle Cloud 控制台
2. 左上角菜单 → **Compute** → **Instances** → **Create instance**
3. 配置：
   - **Image**: Ubuntu 22.04（或最新 LTS）
   - **Shape**: Ampere A1（ARM，免费配额 4核24G，选 1核6G 足够）
     - 或 AMD VM.Standard.E2.1.Micro（x86，免费配额 1核1G）
   - **Add SSH keys**: 选择「Generate a key pair for me」，下载私钥保存好
4. 点击 **Create**，等待实例状态变为 Running

### 3.3 配置防火墙（放行端口）

Oracle 默认有两层防火墙，都需要配置：

**第一层：Oracle 控制台安全列表**
1. 实例详情页 → 点击 **Virtual cloud network** 链接
2. 左侧 **Security Lists** → 点击默认安全列表
3. **Add Ingress Rules**：
   - Source CIDR: `0.0.0.0/0`
   - Destination Port: `22`（SSH，默认已有）
   - （Webhook 模式才需要额外放行 8443，polling 模式不需要）

**第二层：系统内部防火墙**
SSH 登录后执行：
```bash
sudo iptables -I INPUT -p tcp --dport 22 -j ACCEPT
sudo netfilter-persistent save
```

### 3.4 SSH 登录

```bash
# 把下载的私钥放到 ~/.ssh/ 下并设置权限
chmod 600 ~/.ssh/oracle_private.key

# 登录（ubuntu 用户，IP 替换为你的实例公网IP）
ssh -i ~/.ssh/oracle_private.key ubuntu@你的实例公网IP
```

## 四、服务器环境搭建

### 4.1 安装 Python 和依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 3 和 pip
sudo apt install -y python3 python3-pip python3-venv git

# 验证版本（需要 Python 3.10+）
python3 --version
```

### 4.2 上传代码

```bash
# 创建项目目录
mkdir -p ~/tg-order-bot && cd ~/tg-order-bot

# 方式一：用 scp 从本地上传（在本地电脑执行）
# scp -i ~/.ssh/oracle_private.key -r ./tg-order-bot/* ubuntu@你的IP:~/tg-order-bot/

# 方式二：直接在服务器上创建文件，把代码逐个粘贴
# （推荐用 FileZilla 等 SFTP 工具上传，更方便）
```

### 4.3 创建虚拟环境并安装依赖

```bash
cd ~/tg-order-bot

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 如果 phone 库安装失败，尝试：
pip install phone
```

### 4.4 配置机器人

编辑 `config.py`：
```bash
nano config.py
```

修改以下两项：
```python
BOT_TOKEN = "你从BotFather拿到的Token"
SUPER_ADMIN_ID = 123456789  # 你的TG数字ID
```

保存退出（Ctrl+O，回车，Ctrl+X）。

### 4.5 测试运行

```bash
# 先前台运行测试
python3 bot.py
```

看到 `数据库初始化完成` 和 `使用长轮询模式` 就说明启动成功了。

去 Telegram 私聊机器人发 `/start`，应该能看到你的 ID 和授权状态。

按 `Ctrl+C` 停止。

## 五、配置开机自启（systemd）

### 5.1 修改 service 文件

```bash
nano ~/tg-order-bot/tg-order-bot.service
```

确认以下内容正确：
- `User=ubuntu`（如果你的用户名不是 ubuntu 就改）
- `WorkingDirectory=/home/ubuntu/tg-order-bot`
- `ExecStart=/home/ubuntu/tg-order-bot/venv/bin/python /home/ubuntu/tg-order-bot/bot.py`
- `Environment="BOT_TOKEN=你的Token"`
- `Environment="SUPER_ADMIN_ID=你的ID"`

### 5.2 安装并启动服务

```bash
# 复制 service 文件到系统目录
sudo cp ~/tg-order-bot/tg-order-bot.service /etc/systemd/system/

# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start tg-order-bot

# 设置开机自启
sudo systemctl enable tg-order-bot

# 查看状态
sudo systemctl status tg-order-bot

# 查看日志
sudo journalctl -u tg-order-bot -f
```

### 5.3 常用运维命令

```bash
# 重启机器人（修改代码后执行）
sudo systemctl restart tg-order-bot

# 停止
sudo systemctl stop tg-order-bot

# 查看实时日志
sudo journalctl -u tg-order-bot -f

# 查看最近 100 行日志
sudo journalctl -u tg-order-bot -n 100
```

## 六、使用指南

### 6.1 初始化操作员

1. 超级管理员私聊机器人发 `/start`，确认自己已授权
2. 让操作员私聊机器人发 `/start`，获取他的 TG ID
3. 管理员发 `/addop 操作员TG_ID` 添加授权
4. 操作员会收到授权通知

### 6.2 把机器人拉进业务群

1. 在 Telegram 群里 → 添加成员 → 搜索机器人用户名 → 添加
2. 给机器人「管理员」权限（至少需要「删除消息」和「固定消息」权限，方便管理）
3. 在群里发 `/start` 或随便说句话测试

### 6.3 下单

在群里直接发（每行一个订单，支持批量）：
```
15502245331 联通 200 张丹丹
13911322832 移动 300 李明
```

机器人会回复：
```
✅ 15502245331 新增成功
✅ 13911322832 新增成功
```

### 6.4 查单

```
本群订单          # 看统计汇总
本群话费订单      # 看明细，每条带「完成」按钮
```

### 6.5 完成订单

在「本群话费订单」的明细消息里，点击「✅ 充值完成」按钮即可。

部分充值（比如300元订单先充100元）：
```
/recharge 15502245331 100
```

### 6.6 撤单

操作员在群里发：
```
撤单 13810295470 15811188914
```

管理员私聊发 `/cancellist` 查看待审核申请，点击「✅ 同意撤单」按钮。

审核通过后，群内和申请人私聊都会收到撤单成功通知。

### 6.7 话费余额查询

在群里或私聊**直接发一个手机号**（纯11位数字），机器人会自动查询话费余额：

```
13212801772
```

返回结果包含：
- 号码、运营商、话费余额、剩余积分
- 该号码最近 5 条查询记录（余额 + 时间）
- 底部「💳 生成付款链接」按钮

> ⚠️ 余额查询需要接入第三方 API。未配置时使用模拟数据方便测试。
> 配置方法见下方「话费余额查询 API 配置」。

## 七、话费余额查询 API 配置

### 7.1 配置 API

编辑 `config.py`，填入你的余额查询接口：

```python
BALANCE_API_URL = "https://your-api.com/balance"
BALANCE_API_KEY = "your_api_key"
```

### 7.2 适配 API 格式

不同服务商的 API 请求/返回格式不同，需要修改 `balance_api.py` 中的两个方法：

- **`_build_request(phone)`**：构建 API 请求（URL、请求头、参数）
- **`_parse_response(phone, data)`**：解析 API 返回数据，映射到余额、积分、运营商

代码中已用 ⚠️ 标注需要修改的位置，并提供了通用示例。

### 7.3 付款链接配置

编辑 `config.py`：
```python
PAYMENT_URL_TEMPLATE = "https://your-pay.com/pay?phone={phone}"
```
`{phone}` 会自动替换为实际手机号。留空则点击按钮提示未配置。

## 八、数据备份

SQLite 数据库是单个文件 `orders.db`，定期备份即可：

```bash
# 手动备份
cp ~/tg-order-bot/orders.db ~/orders_backup_$(date +%Y%m%d).db

# 设置每天自动备份（crontab）
crontab -e
# 添加一行：每天凌晨3点备份
0 3 * * * cp /home/ubuntu/tg-order-bot/orders.db /home/ubuntu/backup/orders_$(date +\%Y\%m\%d).db
```

## 九、运维脚本

项目自带 `scripts/` 目录，包含四个常用运维脚本：

| 脚本 | 作用 | 用法 |
|---|---|---|
| `setup.sh` | 一键部署（装依赖+配环境+启服务） | `sudo ./scripts/setup.sh`（先修改脚本内的 Token 和管理员ID） |
| `restart.sh` | 重启机器人（改代码后用） | `./scripts/restart.sh` |
| `logs.sh` | 查看日志 | `./scripts/logs.sh -f`（实时）/ `./scripts/logs.sh 100 error`（错误） |
| `backup.sh` | 数据库备份（自动清理30天前） | `./scripts/backup.sh` |

**设置定时自动备份：**
```bash
crontab -e
# 每天凌晨3点自动备份
0 3 * * * /home/ubuntu/tg-order-bot/scripts/backup.sh >> /home/ubuntu/tg-order-bot/backups/backup.log 2>&1
```

## 十、常见问题

**Q: 机器人在群里不回复？**
A: 检查是否关闭了 BotFather 的隐私模式（/setprivacy → Disable），以及机器人是否在群里有管理员权限。

**Q: 手机号地区显示「未知」？**
A: `phone` 库的号段数据可能不全，新号段可能识别不了。不影响核心功能，地区仅作展示。

**Q: Oracle VPS 突然连不上？**
A: Oracle 免费实例可能因闲置被回收。建议保持机器人持续运行（有网络流量），降低被回收概率。也可以设置定时任务模拟活动。

**Q: 想换成 Webhook 模式？**
A: 需要有域名和 SSL 证书。修改 `config.py` 中 `RUN_MODE=webhook`，配置 `WEBHOOK_HOST`，并放行 8443 端口。一般 VPS 上用 polling 更简单稳定。

**Q: 怎么添加电费业务？**
A: 当前版本默认全是话费业务。群绑定功能预留了 `groups` 表结构，后续可扩展：管理员用命令设置群类型（话费/电费），下单时自动归类。

**Q: 余额查询返回的是模拟数据？**
A: 未配置 `BALANCE_API_URL` 时自动进入 mock 模式，返回模拟数据方便测试。配置真实 API 后自动切换。注意不同服务商 API 格式不同，需在 `balance_api.py` 中适配 `_build_request` 和 `_parse_response`。

**Q: 余额查询 API 怎么选？**
A: 常见的话费余额查询接口服务商有：讯联、玖富、易赛等。需要你自己购买或对接 API，机器人只负责调用和展示。拿到 API 文档后，按照 `balance_api.py` 中的注释修改请求和解析即可。

---

## 文件结构

```
tg-order-bot/
├── bot.py                 # 主程序（所有命令和回调逻辑）
├── config.py              # 配置文件（Token、管理员ID、余额API等）
├── db.py                  # 数据库操作层
├── balance_api.py         # 话费余额查询 API 客户端
├── phone_utils.py         # 手机号地区识别工具
├── parser.py              # 群内消息解析器
├── requirements.txt       # Python 依赖
├── tg-order-bot.service   # systemd 服务配置
├── scripts/               # 运维脚本
│   ├── setup.sh           # 一键部署
│   ├── restart.sh         # 重启机器人
│   ├── logs.sh            # 查看日志
│   └── backup.sh          # 数据库备份
└── README.md              # 本文件
```
