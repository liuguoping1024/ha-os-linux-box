# Zigbee2MQTT 集成指南

本文档说明如何在 ThirdReality HubV3 项目中集成 Zigbee2MQTT。

## 已完成的工作

### 1. 创建的包结构

```
buildroot-external/package/
├── zigbee-herdsman/
│   ├── Config.in
│   └── zigbee-herdsman.mk
└── zigbee2mqtt/
    ├── Config.in
    ├── zigbee2mqtt.mk
    ├── zigbee2mqtt.service
    ├── README.md
    ├── configs/
    │   └── README.md
    └── converters/
        └── README.md
```

### 2. 更新的配置文件

- ✅ `buildroot-external/Config.in` - 添加了 zigbee-herdsman 和 zigbee2mqtt 的源引用
- ✅ `buildroot-external/configs/thirdreality_hubv3_defconfig` - 启用了所有必要的包

### 3. 添加的依赖包

在 defconfig 中启用了：
- `BR2_PACKAGE_MOSQUITTO=y` - MQTT broker (版本 2.0.20)
- `BR2_PACKAGE_MOSQUITTO_BROKER=y` - MQTT broker 守护进程
- `BR2_PACKAGE_NODEJS=y` - Node.js 运行时 (版本 20.18.2)
- `BR2_PACKAGE_NODEJS_NPM=y` - NPM 包管理器
- `BR2_PACKAGE_ZIGBEE_HERDSMAN=y` - 定制的 zigbee-herdsman
- `BR2_PACKAGE_ZIGBEE2MQTT=y` - 定制的 zigbee2mqtt

## 下一步需要做的事情

### 1. 添加配置文件

将你的配置文件复制到以下位置：

```bash
# 从你的原始脚本目录复制
cp /path/to/your/prebuild/configuration_zigate.yaml \
   buildroot-external/package/zigbee2mqtt/configs/

cp /path/to/your/prebuild/configuration_blz.yaml \
   buildroot-external/package/zigbee2mqtt/configs/
```

### 2. 添加外部转换器（如果有）

如果你有自定义的设备转换器：

```bash
# 复制转换器文件
cp /path/to/your/prebuild/converters/*.js \
   buildroot-external/package/zigbee2mqtt/converters/
```

### 3. 构建系统

```bash
cd /root/linuxbox/ha-os-linux-box

# 应用配置
make thirdreality_hubv3_defconfig

# 构建（首次构建会下载所有依赖）
make
```

### 4. 增量构建（如果需要修改）

```bash
# 只重新构建 zigbee2mqtt
make zigbee2mqtt-rebuild

# 只重新构建 zigbee-herdsman
make zigbee-herdsman-rebuild

# 清理后重新构建
make zigbee2mqtt-dirclean
make zigbee2mqtt
```

## 与原始脚本的对比

### 原始 DEB 构建方式：
```bash
git clone -b 3r_blz_7.0.3 https://github.com/thirdreality/zigbee-herdsman.git
cd zigbee-herdsman
pnpm install --no-frozen-lockfile && pnpm run build

git clone -b 3r_blz_2.7.0 https://github.com/thirdreality/zigbee2mqtt.git
cd zigbee2mqtt
pnpm install --no-frozen-lockfile && pnpm run build
```

### 现在的 Buildroot 方式：
- Buildroot 自动处理 git clone
- Buildroot 自动处理 pnpm 安装和构建
- 配置文件和转换器在构建时自动复制
- systemd 服务自动安装

## 版本信息

| 组件 | 原需求版本 | 实际使用版本 | 说明 |
|------|-----------|-------------|------|
| Node.js | 24.12.0 | 20.18.2 | Buildroot 自带，向下兼容 |
| Mosquitto | 2.0.11 | 2.0.20 | Buildroot 自带，向上兼容 |
| zigbee-herdsman | 3r_blz_7.0.3 | 3r_blz_7.0.3 | 定制版本，完全一致 |
| zigbee2mqtt | 3r_blz_2.7.0 | 3r_blz_2.7.0 | 定制版本，完全一致 |

## 功能特性

### ✅ 已实现
- 从 GitHub 自动克隆定制版本的代码
- 使用 pnpm 安装依赖
- 自动构建
- systemd 服务集成
- 配置文件自动安装
- 外部转换器自动安装
- Mosquitto MQTT broker 集成

### 🔧 可选优化

如果你需要使用腾讯镜像加速 npm 包下载，可以修改 makefile：

```makefile
# 在 zigbee-herdsman.mk 和 zigbee2mqtt.mk 中
pnpm install --no-frozen-lockfile --registry=https://mirrors.tencent.com/npm/
```

## 服务管理

系统启动后，Zigbee2MQTT 作为 systemd 服务运行：

```bash
# 启动服务
systemctl start zigbee2mqtt

# 查看状态
systemctl status zigbee2mqtt

# 查看日志
journalctl -u zigbee2mqtt -f

# 开机自启
systemctl enable zigbee2mqtt
```

## 文件布局

构建完成后的目标系统文件布局：

```
/opt/
├── zigbee-herdsman/          # zigbee-herdsman 库
│   ├── dist/                 # 编译后的代码
│   ├── node_modules/         # 依赖包
│   └── package.json
└── zigbee2mqtt/              # zigbee2mqtt 主程序
    ├── dist/                 # 编译后的代码
    ├── node_modules/         # 依赖包
    ├── data/                 # 数据目录
    │   ├── configuration_zigate.yaml
    │   ├── configuration_blz.yaml
    │   └── external_converters/
    │       └── *.js          # 自定义转换器
    └── package.json

/usr/lib/systemd/system/
└── zigbee2mqtt.service       # systemd 服务文件
```

## 故障排查

### 构建失败

1. **网络问题**
   ```bash
   # 检查能否访问 GitHub
   ping github.com
   
   # 检查能否访问 npm registry
   curl -I https://registry.npmjs.org
   ```

2. **清理缓存**
   ```bash
   make zigbee2mqtt-dirclean
   make zigbee-herdsman-dirclean
   make clean
   ```

3. **查看构建日志**
   ```bash
   # 日志位置
   output/build/zigbee-herdsman-*/
   output/build/zigbee2mqtt-*/
   ```

### 运行时问题

1. **服务无法启动**
   ```bash
   # 查看详细日志
   journalctl -u zigbee2mqtt -n 100 --no-pager
   
   # 检查依赖服务
   systemctl status mosquitto
   ```

2. **找不到 USB 设备**
   ```bash
   # 列出 USB 设备
   ls -l /dev/ttyUSB*
   ls -l /dev/ttyACM*
   
   # 检查权限
   id
   ```

3. **MQTT 连接失败**
   ```bash
   # 测试 MQTT 连接
   mosquitto_sub -h localhost -t '#' -v
   ```

## 技术细节

### 依赖关系图

```
zigbee2mqtt
├── nodejs (运行时)
├── npm (包管理)
├── pnpm (包管理，运行时安装)
├── mosquitto (MQTT broker)
└── zigbee-herdsman (定制库)
    ├── nodejs
    └── pnpm
```

### 构建顺序

1. nodejs (Buildroot 内置)
2. mosquitto (Buildroot 内置)
3. zigbee-herdsman (自定义包)
4. zigbee2mqtt (自定义包，依赖 zigbee-herdsman)

### 磁盘空间需求

估算的磁盘空间使用：
- Node.js 运行时: ~50MB
- npm 包缓存: ~200MB (构建时)
- zigbee-herdsman: ~30MB
- zigbee2mqtt: ~100MB
- mosquitto: ~5MB
- **总计**: ~385MB (运行时 ~185MB)

## 联系与支持

如果遇到问题：
1. 查看构建日志
2. 检查 systemd 服务状态
3. 查看应用日志
4. 参考官方文档: https://www.zigbee2mqtt.io/

## 更新日志

- 2024-02-12: 初始集成完成
  - 添加 zigbee-herdsman 包
  - 添加 zigbee2mqtt 包
  - 配置 systemd 服务
  - 更新 defconfig
