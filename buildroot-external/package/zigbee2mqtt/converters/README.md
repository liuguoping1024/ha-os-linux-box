# Zigbee2MQTT 外部转换器

将你的自定义设备转换器 JavaScript 文件放在这个目录中。

## 用途

外部转换器用于支持 Zigbee2MQTT 官方尚未支持的自定义 Zigbee 设备。

## 文件格式

转换器文件应该是标准的 JavaScript 模块，例如：

```javascript
// custom_device.js
const fz = require('zigbee-herdsman-converters/converters/fromZigbee');
const tz = require('zigbee-herdsman-converters/converters/toZigbee');
const exposes = require('zigbee-herdsman-converters/lib/exposes');
const reporting = require('zigbee-herdsman-converters/lib/reporting');
const e = exposes.presets;

const definition = {
    zigbeeModel: ['CUSTOM_MODEL'],
    model: 'CUSTOM_MODEL',
    vendor: 'ThirdReality',
    description: 'Custom device description',
    fromZigbee: [fz.on_off],
    toZigbee: [tz.on_off],
    exposes: [e.switch()],
};

module.exports = definition;
```

## 安装位置

这些文件将被复制到目标系统的 `/opt/zigbee2mqtt/data/external_converters/` 目录。

## 使用方法

在 Zigbee2MQTT 配置文件中引用外部转换器：

```yaml
external_converters:
  - custom_device.js
```

## 注意事项

- 只放置 `.js` 文件
- 确保文件名不包含空格
- 文件必须是有效的 JavaScript 语法
- 测试转换器后再添加到构建中
