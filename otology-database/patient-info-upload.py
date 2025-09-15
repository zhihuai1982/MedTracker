import pandas as pd
from sqlalchemy import create_engine, text, String, Float, DateTime, Integer

# 读取Excel文件并处理数据
excel_file = "2025-07月至2025-09月病例数据统计表.xlsx"
df = pd.read_excel(excel_file, skiprows=1, header=0)

# 定义列名映射
existing_columns = [
    "患者姓名",
    "住院号",
    "病案号",
    "医生",
    "主要诊断",
    "主要手术",
    "其他手术",
    "年龄",
    "入院日期",
    "出院科室",
    "DRG医疗总费用",
    "自费金额",
    "个人现金支付",
    "险种类型",
]
column_mapping = {
    "患者姓名": "name",
    "住院号": "adn",
    "病案号": "mrn",
    "医生": "attending",
    "主要诊断": "primaryDiagnose",
    "主要手术": "primarySurgery",
    "其他手术": "secondarySurgery",
    "年龄": "age",
    "入院日期": "admissionDate",
    "出院科室": "campus",
}

# 提取并处理数据
patient_info_df = df[existing_columns].rename(columns=column_mapping).copy()

# 提取series列
patient_info_df["series"] = patient_info_df["adn"].apply(
    lambda x: str(x).split("-")[-1] if "-" in str(x) else str(x)
)
patient_info_df["series"] = (
    pd.to_numeric(patient_info_df["series"], errors="coerce").fillna(0).astype(int)
)

# 统一转换为字符串类型
for col in ["primaryDiagnose", "primarySurgery", "secondarySurgery"]:
    patient_info_df[col] = patient_info_df[col].astype(str)

# 构建筛选条件
condition1 = (patient_info_df["primaryDiagnose"].str.contains("中耳", na=False)) & (
    ~patient_info_df["primaryDiagnose"].str.contains("分泌性", na=False)
)
condition2 = patient_info_df["primarySurgery"].str.contains(
    "鼓室成型|乳突|听骨链", na=False
)
condition3 = patient_info_df["secondarySurgery"].str.contains(
    "鼓室成型|乳突|听骨链", na=False
)
screened_patient_df = patient_info_df[condition1 | condition2 | condition3].copy()

# 数据清洗和类型转换
screened_patient_df = screened_patient_df.astype(
    {
        "primaryDiagnose": "str",
        "primarySurgery": "str",
        "secondarySurgery": "str",
        "DRG医疗总费用": "float",
        "自费金额": "float",
        "个人现金支付": "float",
    }
)
screened_patient_df["age"] = (
    screened_patient_df["age"].str.replace("岁", "").astype(int)
)
screened_patient_df["admissionDate"] = pd.to_datetime(
    screened_patient_df["admissionDate"]
)

# 数据库类型映射
dtype_mapping = {
    "name": String(20),
    "adn": String(50),
    "mrn": String(50),
    "attending": String(20),
    "primaryDiagnose": String(255),
    "primarySurgery": String(255),
    "secondarySurgery": String(255),
    "age": Integer(),
    "admissionDate": DateTime(),
    "campus": String(100),
    "series": String(10),
    "DRG医疗总费用": Float(),
    "自费金额": Float(),
    "个人现金支付": Float(),
    "险种类型": String(20),
}

# 数据预览
print(
    f"筛选后的患者信息数据预览：\n{screened_patient_df.head()}\n\n筛选后共{len(screened_patient_df)}条符合条件的记录。"
)

# 数据库连接和操作
db_config = {
    "host": "www.digitalnomad.host",
    "port": 5432,
    "database": "otology-db",
    "user": "zhihuai1982",
    "password": "pg-password",
}
engine = create_engine(
    f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
)

# 获取现有记录并处理重复数据
existing_adn = []
if "adn" in screened_patient_df.columns:
    with engine.connect() as conn:
        try:
            # 添加主键约束（如果需要）
            try:
                conn.execute(
                    text("ALTER TABLE patient_admission_record ADD PRIMARY KEY (adn)")
                )
                conn.commit()
            except Exception:
                pass  # 主键可能已存在
                conn.rollback()

            # 查询现有adn
            existing_adn = (
                pd.read_sql("SELECT adn FROM patient_admission_record", conn)["adn"]
                .astype(str)
                .tolist()
            )
        except Exception as e:
            print(f"查询现有记录时出错: {e}")

    # 筛选新数据
    screened_patient_df["adn"] = screened_patient_df["adn"].astype(str)
    new_data = screened_patient_df[
        ~screened_patient_df["adn"].isin(existing_adn)
    ].copy()

    # 处理本地重复
    if new_data.duplicated("adn").any():
        print(
            f"警告: 本地数据中发现{new_data.duplicated('adn').sum()}个重复的adn值，将只保留第一个出现的记录"
        )
        new_data = new_data.drop_duplicates("adn", keep="first")

    print(f"筛选后共有{len(new_data)}条新记录待上传")
else:
    print("错误: DataFrame中不存在adn列")
    new_data = pd.DataFrame()

# 上传数据
try:
    if not new_data.empty:
        new_data.to_sql(
            name="patient_admission_record",
            con=engine,
            if_exists="append",
            index=False,
            dtype=dtype_mapping,
            method="multi",
        )
        print(f"成功上传{len(new_data)}条新记录到数据库")

        # 验证上传结果
        with engine.connect() as conn:
            total_count = pd.read_sql(
                "SELECT COUNT(*) FROM patient_admission_record", conn
            ).iloc[0, 0]
            print(f"数据库表中现有 {total_count} 条记录")
    else:
        print("没有新的记录需要上传")
except Exception as e:
    print(f"上传数据时出错: {e}")
