# Render 免费部署教程（不需要信用卡）

> 适用：完全零基础，没有信用卡，想免费部署 Telegram 机器人
> 平台：Render（免费层）+ GitHub（免费）
> 预计耗时：30-40 分钟
> 费用：0 元

---

## 为什么用 Render？

- ✅ **完全免费**，不需要信用卡
- ✅ 注册简单，邮箱就行
- ✅ 提供免费域名（`https://你的项目名.onrender.com`）+ HTTPS
- ✅ 自动部署，推送代码就更新
- ⚠️ 免费层 15 分钟无请求会休眠，但 Telegram 发消息会自动唤醒（唤醒约需 5-10 秒）

---

## 整体流程（共 6 大步）

```
1. 注册 GitHub 账号 → 2. 上传代码到 GitHub → 3. 注册 Render
→ 4. 连接 GitHub 部署 → 5. 填配置 → 6. 完成！
```

---

## 第一步：注册 GitHub 账号

GitHub 是一个代码托管平台，Render 需要从 GitHub 拉取你的代码。

1. 打开浏览器，访问：https://github.com
2. 点击右上角 **Sign up**（注册）
3. 输入你的邮箱（推荐 Gmail/Outlook），点击 **Continue**
4. 设置密码，点击 **Continue**
5. 设置用户名（随便取，比如 `zhangsan2024`），点击 **Continue**
6. 问你是否要接收产品更新，选 **No** 或 **Yes** 都行，点击 **Continue**
7. 完成拼图验证
8. 去邮箱查收 GitHub 的验证邮件，点击 **Verify email address**
9. 验证成功后，会跳转到 GitHub 主页，注册完成

> 💡 用户名要记一下，后面会用到。

---

## 第二步：创建 GitHub 仓库并上传代码

### 2.1 创建仓库

1. 登录 GitHub 后，点击右上角 **+** 号 → **New repository**（新建仓库）
2. **Repository name**（仓库名）：填 `tg-order-bot`
3. **Description**（描述）：可以不填
4. 选择 **Public**（公开，免费）
5. 勾选 **Add a README file**（添加 README 文件）
6. 点击底部绿色按钮 **Create repository**（创建仓库）

### 2.2 上传代码文件

1. 仓库创建好后，点击 **Add file** → **Upload files**（上传文件）
2. 把你电脑上解压后的 `tg-order-bot` 文件夹里的**所有文件**（不是文件夹本身）拖到上传区域
   - 应该包括：`bot.py`、`config.py`、`db.py`、`balance_api.py`、`phone_utils.py`、`parser.py`、`requirements.txt`、`render.yaml`、`README.md`、`零基础部署手册.md`、`scripts/` 文件夹等
   - 注意：不要上传 `__pycache__` 文件夹和 `orders.db` 数据库文件（如果有的话）
3. 等待上传完成
4. 滚动到页面底部，点击绿色按钮 **Commit changes**（提交更改）
5. 上传完成后，你应该能在仓库页面看到所有文件

> ⚠️ 重要：确认 `render.yaml` 文件已经上传上去了，这个文件是 Render 自动配置的关键。

---

## 第三步：注册 Render 账号

1. 打开浏览器，访问：https://render.com
2. 点击右上角 **Get Started** 或 **Sign Up**
3. 选择 **Sign up with GitHub**（用 GitHub 账号登录，最方便）
4. 会跳转到 GitHub 授权页面，点击 **Authorize renderinc**（授权 Render 访问你的 GitHub）
5. 填写一些基本信息（姓名、公司可以填 "Personal"），点击 **Continue**
6. 问你要选择哪个计划，选择 **Free**（免费）
7. 注册完成，进入 Render 控制台

> 💡 用 GitHub 登录 Render 后，Render 就能直接看到你的 GitHub 仓库，不需要再手动连接。

---

## 第四步：在 Render 上部署机器人

### 4.1 创建 Web Service

1. 在 Render 控制台，点击右上角 **New +** → **Web Service**（Web 服务）
2. 页面会显示你的 GitHub 仓库列表
3. 找到 `tg-order-bot` 仓库，点击右边的 **Connect**（连接）
4. Render 会自动读取 `render.yaml` 配置，大部分字段已经预填好了

### 4.2 确认配置

检查以下字段（大部分已经自动填好，不需要改）：

- **Name**（名称）：`tg-order-bot`（这个会成为你的域名一部分）
- **Region**（区域）：选 `Oregon (US West)` 或 `Frankfurt (EU Central)`，选离你近的
- **Runtime**（运行环境）：`Python 3`
- **Build Command**（构建命令）：`pip install -r requirements.txt`
- **Start Command**（启动命令）：`python bot.py`
- **Instance Type**（实例类型）：选 **Free**（免费）

### 4.3 填写环境变量（关键！）

滚动到 **Environment Variables**（环境变量）区域，需要手动填两个：

| Key（变量名） | Value（值） | 说明 |
|---|---|---|
| `BOT_TOKEN` | 你的机器人 Token | 从 @BotFather 获取，类似 `123456:ABCdef...` |
| `SUPER_ADMIN_ID` | 先填 `0` | 等部署后获取你的 ID 再改 |

> ⚠️ `BOT_TOKEN` 必须填，否则机器人连不上 Telegram。
> `SUPER_ADMIN_ID` 先填 0，部署成功后再改。

其他环境变量（`BALANCE_API_URL`、`PAYMENT_URL_TEMPLATE` 等）可以先不填，留空即可。

### 4.4 开始部署

1. 确认所有配置无误后，点击页面底部的 **Create Web Service**（创建 Web 服务）
2. Render 会开始构建和部署，页面会显示实时日志
3. 第一次部署需要 2-5 分钟（安装依赖）
4. 当日志显示 `Your service is live 🎉` 时，说明部署成功！

> 💡 如果部署失败，查看日志里的红色错误信息，把错误发给我帮你排查。

---

## 第五步：获取你的 TG ID 并更新配置

### 5.1 获取 ID

1. 打开 Telegram，找到你的机器人，发 `/start`
2. 机器人会回复你的 ID，类似：
   ```
   👋 欢迎！
   您的 ID：123456789
   您尚未获得授权...
   ```
3. 把这个数字 ID 记下来

### 5.2 更新 Render 配置

1. 回到 Render 控制台，进入你的 `tg-order-bot` 服务
2. 点击左侧 **Environment**（环境）
3. 找到 `SUPER_ADMIN_ID`，点击右边的编辑图标（铅笔）
4. 把值从 `0` 改成你的 ID 数字（比如 `123456789`）
5. 点击 **Save Changes**（保存更改）
6. Render 会自动重新部署，等待 1-2 分钟

### 5.3 验证

重新部署完成后，再次私聊机器人发 `/start`，应该显示：
```
🎉 您已获【话费车】权限（管理员）
现在可在业务群上单...
```

说明你已经是超级管理员了！

---

## 第六步：配置 Telegram 机器人

### 6.1 关闭隐私模式（必须！）

1. 在 Telegram 搜索 **@BotFather**
2. 发送 `/setprivacy`
3. 选择你的机器人
4. 点击 **Disable**（关闭）
5. 显示 `Privacy mode is disabled` 就成功了

> ⚠️ 不关闭的话，机器人在群里读不到普通消息，只能读到命令。

### 6.2 设置命令菜单（推荐）

在 @BotFather 发送 `/setcommands`，选择你的机器人，粘贴：

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

### 6.3 把机器人拉进业务群

1. 打开你的 Telegram 群
2. 点击群名 → 编辑 → 管理员 → 添加管理员
3. 搜索你的机器人，添加
4. 给机器人权限：删除消息、固定消息

---

## 第七步：开始使用

### 群内下单

在群里直接发（每行一个，支持批量）：
```
15502245331 联通 200 张丹丹
13911322832 移动 300 李明
```

### 查看订单

```
本群订单        # 统计
本群话费订单    # 明细（带完成按钮）
```

### 撤单

```
撤单 13810295470 15811188914
```

管理员私聊发 `/cancellist` 审核。

### 查话费余额

直接发一个手机号：
```
13212801772
```

---

## 常见问题

**Q: Render 免费层休眠了怎么办？**
A: 正常现象。有人在 Telegram 发消息时，webhook 请求会自动唤醒机器人，第一次响应可能慢 5-10 秒，之后就正常了。如果想 24 小时不休眠，可以用 UptimeRobot（免费）定时 ping 你的 Render 域名。

**Q: 数据库会丢失吗？**
A: Render 免费层的文件系统在**重新部署**时会重置。也就是说，只要你不手动重新部署，数据不会丢。但如果更新了代码重新部署，`orders.db` 会被清空。建议定期用 `/search` 查看重要订单，或者升级 Render 付费版添加持久磁盘。

**Q: 怎么更新代码？**
A: 把修改后的文件重新上传到 GitHub 仓库（覆盖原文件），Render 会检测到变化并自动重新部署。注意重新部署会清空数据库。

**Q: 部署失败了怎么办？**
A: 在 Render 服务页面点击 **Logs**（日志），查看红色错误信息。最常见的原因是 `BOT_TOKEN` 填错了，或者 `requirements.txt` 里的依赖安装失败。把错误截图发给我帮你排查。

**Q: 机器人在群里不回复？**
A: 检查三件事：① @BotFather 关闭了隐私模式；② 机器人在群里是管理员；③ Render 上服务状态是 "Live"（不是休眠中）。

**Q: Render 免费版有什么限制？**
A: 每月 750 小时运行时间（单实例 24x7 够用），0.1 CPU 核心，512MB 内存。对于这个机器人完全够用。15 分钟无请求会休眠。

---

## 快速参考

| 项目 | 值 |
|---|---|
| Render 控制台 | https://dashboard.render.com |
| 你的机器人地址 | `https://tg-order-bot.onrender.com`（如果名字被占用会变） |
| Webhook 地址 | `https://tg-order-bot.onrender.com/webhook` |
| 健康检查 | `https://tg-order-bot.onrender.com/` |
| GitHub 仓库 | `https://github.com/你的用户名/tg-order-bot` |

---

**按照这个教程一步步来，一定能搞定！** 哪一步卡住了，把截图或错误信息发给我。
