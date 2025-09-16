# %%
import pandas as pd
from sqlalchemy import create_engine, text, String, Float, DateTime, Integer
import requests
from io import StringIO
from datetime import datetime
import re

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
# 添加条件：删除primaryDiagnose为空的行
condition_empty = patient_info_df["primarySurgery"].str.strip() != "-"

# 应用所有条件
screened_patient_df = patient_info_df[
    (condition1 | condition2 | condition3) & condition_empty
][:3].copy()


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
screened_patient_df["admissionDate"] = screened_patient_df["admissionDate"].dt.strftime(
    "%Y-%m-%d"
)


# 数据预览
print(
    f"筛选后的患者信息数据预览：\n{screened_patient_df.head()}\n\n筛选后共{len(screened_patient_df)}条符合条件的记录。"
)


# %%
# 添加手术相关信息

# 初始化新列
screened_patient_df["surgeryDate"] = pd.NaT
screened_patient_df["surgeryDuration"] = None
screened_patient_df["surgical_findings"] = None

# 设置请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"
}

# 遍历DataFrame中的每一行
for index, row in screened_patient_df.iterrows():
    try:
        mrn = row["mrn"]
        series = row["series"]

        print(f"正在处理患者MRN: {mrn}, Series: {series}")

        # 获取文档列表
        hDocuList = requests.get(
            f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/{mrn}/{series}/emr",
            headers=headers,
            timeout=10,
        ).json()

        # 筛选出"手术记录"
        surgeryList = [item for item in hDocuList if item.get("docname") == "手术记录"]

        if not surgeryList:
            print(f"未找到患者 {mrn} 的手术记录")
            continue

        # 获取手术记录内容
        surgeryurl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{surgeryList[0]['id']}/{surgeryList[0]['prlog_rdn']}/"
        response = requests.get(surgeryurl, headers=headers, timeout=10)

        # 从HTML中读取表格数据
        tables = pd.read_html(StringIO(response.text))

        # 提取手术相关信息
        surgeryDate = tables[2].iloc[0, 1]
        surgeryDuration = tables[2].iloc[3, 3]
        surgeon = tables[2].iloc[0, 3]
        surgical_findings = tables[3].iloc[7, 0]

        # 更新DataFrame
        screened_patient_df.at[index, "surgeryDate"] = surgeryDate
        screened_patient_df.at[index, "surgeryDuration"] = surgeryDuration
        screened_patient_df.at[index, "surgeon"] = surgeon
        screened_patient_df.at[index, "surgical_findings"] = surgical_findings

    except Exception as e:
        print(f"处理患者 {mrn} 时出错: {str(e)}")
        # 出错时保持原列为空值
        continue

screened_patient_df["surgeryDuration"] = (
    screened_patient_df["surgeryDuration"].str.replace("分", "").astype(int)
)
screened_patient_df["surgeryDate"] = pd.to_datetime(screened_patient_df["surgeryDate"])
screened_patient_df["surgeryDate"] = screened_patient_df["surgeryDate"].dt.strftime(
    "%Y-%m-%d"
)

# 数据预览（包含手术信息）
print("\n添加手术信息后的数据预览：")
print(
    screened_patient_df[
        ["mrn", "series", "surgeryDate", "surgeryDuration", "surgical_findings"]
    ].head()
)


# %%
# 创建picDir列，格式为：surgeryDate-name-mrn-surgon-primarySurgery

screened_patient_df["picDir"] = (
    screened_patient_df["surgeryDate"].astype(str)
    + "-"
    + screened_patient_df["name"].fillna("unknown")
    + "-"
    + screened_patient_df["mrn"].astype(str)
    + "-"
    + screened_patient_df["surgeon"].fillna("unknown")
    + "-"
    + screened_patient_df["primarySurgery"]
    .fillna("unknown")
    .astype(str)
    .str.replace(r"\([^)]*\)", "", regex=True)
    .str.strip()
)


# %%

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
    "surgeryDate": DateTime(),
    "surgeryDuration": String(10),
    "surgeon": String(10),
    "surgical_findings": String(255),
    "picDir": String(255),
}

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

with engine.connect() as conn:
    try:
        # 检查表是否存在，如果不存在则创建
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS patient_admission_record (
                    "adn" VARCHAR(50) PRIMARY KEY,
                    "name" VARCHAR(20),
                    "mrn" VARCHAR(50),
                    "attending" VARCHAR(20),
                    "surgeon" VARCHAR(10),
                    "primaryDiagnose" VARCHAR(255),
                    "primarySurgery" VARCHAR(255),
                    "secondarySurgery" VARCHAR(255),
                    "age" INTEGER,
                    "admissionDate" DATE,
                    "campus" VARCHAR(100),
                    "series" VARCHAR(10),
                    "DRG医疗总费用" FLOAT,
                    "自费金额" FLOAT,
                    "个人现金支付" FLOAT,
                    "险种类型" VARCHAR(20),
                    "surgeryDate" DATE,
                    "surgeryDuration" INTEGER,
                    "surgical_findings" VARCHAR(255),
                    "picDir" VARCHAR(255)
                )
                """
            )
        )
        conn.commit()
        print("patient_admission_record表创建成功或已存在")

        # 查询现有adn
        existing_adn = (
            pd.read_sql("SELECT adn FROM patient_admission_record", conn)["adn"]
            .astype(str)
            .tolist()
        )
    except Exception as e:
        print(f"创建表时出错: {e}")
        conn.rollback()

# 筛选新数据
screened_patient_df["adn"] = screened_patient_df["adn"].astype(str)
new_data = screened_patient_df[~screened_patient_df["adn"].isin(existing_adn)].copy()

# 处理本地重复
if new_data.duplicated("adn").any():
    print(
        f"警告: 本地数据中发现{new_data.duplicated('adn').sum()}个重复的adn值，将只保留第一个出现的记录"
    )
    new_data = new_data.drop_duplicates("adn", keep="first")

print(f"筛选后共有{len(new_data)}条新记录待上传")

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


# %%
