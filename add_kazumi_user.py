#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加 kazumi 測試用戶到數據庫的腳本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from datetime import date
from werkzeug.security import generate_password_hash
from models import get_engine, SessionLocal, User, UserLevel, Admin, AdminLevel

def add_kazumi_user():
    """添加 kazumi 用戶到數據庫"""
    
    # 初始化數據庫連接
    engine = get_engine(echo=True)
    
    with SessionLocal() as session:
        # 檢查用戶是否已存在
        existing_user = session.query(User).filter_by(account="kazumi").first()
        if existing_user:
            print(f"用戶 kazumi 已存在，ID: {existing_user.id}")
            return existing_user
        
        # 創建新用戶
        kazumi_user = User(
            account="kazumi",
            password=generate_password_hash("kazumi"),
            name="Kazumi Test User",
            email="kazumi@example.com",
            phone="0987654321",
            address="台北市中山區",
            birthday=date(1995, 3, 15),
            register_ip="127.0.0.1",
            wallet=1000,
            award=500,
            referee_id=None,
            level=UserLevel.SECOND
        )
        
        session.add(kazumi_user)
        session.flush()  # 獲取用戶ID
        
        print(f"成功創建用戶 kazumi，ID: {kazumi_user.id}")
        
        # 同時創建管理員權限記錄（可選）
        admin_record = Admin(
            store_id=1,  # 默認商店ID
            user_id=kazumi_user.id,
            level=AdminLevel.MANAGER
        )
        
        session.add(admin_record)
        session.commit()
        
        print(f"已為 kazumi 用戶添加管理員權限（MANAGER 級別）")
        
        return kazumi_user

if __name__ == "__main__":
    try:
        user = add_kazumi_user()
        print(f"\n✅ 成功添加用戶:")
        print(f"   帳號: {user.account}")
        print(f"   姓名: {user.name}")
        print(f"   電子郵件: {user.email}")
        print(f"   密碼雜湊: {user.password}")
        print(f"   用戶等級: {user.level}")
        print(f"   錢包餘額: {user.wallet}")
        print(f"   獎金餘額: {user.award}")
        
    except Exception as e:
        print(f"❌ 添加用戶失敗: {str(e)}")
        sys.exit(1)
