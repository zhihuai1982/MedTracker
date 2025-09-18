import pandas as pd
from sqlalchemy import create_engine, text
import os

# 数据库连接配置
# 从repoNo_get.py中参考的数据库配置
db_config = {
    "host": "www.digitalnomad.host",
    "port": 5432,
    "database": "otology-db",
    "user": "zhihuai1982",
    "password": "pg-password",
}

# 创建数据库连接引擎
engine = create_engine(
    f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
)

try:
    print("开始从数据库下载isLocalImageExist为false的记录...")
    # 使用现有的数据库连接引擎读取表数据
    with engine.connect() as conn:
        # 读取examination_record表中isLocalImageExist为false的记录
        examination_df = pd.read_sql(
            "SELECT * FROM examination_record WHERE \"isLocalImageExist\" = 'false'",
            conn,
        )

        print(f"成功下载{len(examination_df)}条记录")

        # 遍历数据
        for index, row in examination_df.iterrows():
            # 构建文件路径
            # 注意：这里假设picdir列存储的是相对路径或绝对路径的一部分
            # 您可能需要根据实际情况调整路径构建逻辑
            file_path = f"d:\\otology-pic\\{row['picdir']}\\{row['picname']}.jpg"

            # 检查文件是否存在
            if os.path.exists(file_path):
                print(f"文件存在: {file_path}")
                # 更新数据库中的isLocalImageExist列
                try:
                    with engine.connect() as update_conn:
                        update_conn.execute(
                            text(
                                "UPDATE examination_record SET \"isLocalImageExist\" = 'true' WHERE repo = :repo"
                            ),
                            {"repo": row["repo"]},
                        )
                        update_conn.commit()
                        print(f"  已更新repo {row['repo']} 的isLocalImageExist为true")
                except Exception as e:
                    print(f"  更新repo {row['repo']} 时出错: {e}")
            else:
                print(f"文件不存在: {file_path}")

        print("处理完成！")

except Exception as e:
    print(f"处理过程中出错: {e}")
