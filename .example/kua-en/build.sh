#!/bin/bash

# 编译Rust程序
echo "正在编译Rust程序..."
cargo build --release

# 检查编译是否成功
if [ $? -eq 0 ]; then
    echo "Rust程序编译成功!"
    
    # 将编译好的程序复制到目标位置
    cp target/release/english_dict_lookup ./english_dict_lookup
    
    echo "程序已复制到当前目录"
else
    echo "Rust程序编译失败!"
    exit 1
fi