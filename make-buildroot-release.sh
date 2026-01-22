#!/bin/bash


current_dir=$(pwd)
echo "Working directory is '$current_dir'"

# 源代码初始化脚本

# 检查buildroot目录是否为空或不存在
if [ ! -d "${current_dir}/buildroot" ] || [ -z "$(ls -A ${current_dir}/buildroot 2>/dev/null)" ]; then
    # 如果buildroot目录不存在或者为空目录
    echo "buildroot目录不存在或为空,开始初始化..."
    /usr/bin/git pull && /usr/bin/git submodule update --init --recursive
    /usr/bin/git submodule sync
else
    # 如果buildroot目录存在且有多个目录
    echo "buildroot目录已存在且有内容,开始更新..."
    /usr/bin/git pull --recurse-submodules
    /usr/bin/git submodule update --remote --recursive
fi

echo "源代码初始化/更新完成!"

mkdir -p /cache
mkdir -p /build

/usr/bin/make -C ${current_dir}/buildroot O=${current_dir}/output BR2_EXTERNAL=${current_dir}/buildroot-external "khadas_vim3_defconfig"

/usr/bin/make -C ${current_dir}/buildroot O=${current_dir}/output BR2_EXTERNAL=${current_dir}/buildroot-external

