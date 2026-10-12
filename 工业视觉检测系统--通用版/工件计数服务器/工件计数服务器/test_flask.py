#!/usr/bin/env python3
"""
测试Flask服务器是否正常运行
"""

import requests
import time

def test_flask_server():
    print("正在测试Flask服务器...")
    
    test_urls = [
        "http://localhost:5000/api/test",
        "http://127.0.0.1:5000/api/test",
        "http://192.168.1.7:5000/api/test"
    ]
    
    for url in test_urls:
        try:
            print(f"\n测试地址: {url}")
            response = requests.get(url, timeout=5)
            print(f"状态码: {response.status_code}")
            print(f"响应内容: {response.json()}")
            print("✅ 连接成功")
        except requests.exceptions.ConnectionError:
            print("❌ 连接失败 - 无法连接到服务器")
        except requests.exceptions.Timeout:
            print("❌ 连接超时")
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print("\n" + "="*50)
    print("测试API端点: /api/stats")
    
    test_stats_urls = [
        "http://localhost:5000/api/stats",
        "http://192.168.1.7:5000/api/stats"
    ]
    
    for url in test_stats_urls:
        try:
            print(f"\n测试地址: {url}")
            response = requests.get(url, timeout=5)
            print(f"状态码: {response.status_code}")
            print(f"响应内容: {response.json()}")
            print("✅ API正常工作")
        except Exception as e:
            print(f"❌ 错误: {e}")

if __name__ == "__main__":
    test_flask_server()
