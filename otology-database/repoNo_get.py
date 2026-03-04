# %% 导入所需库
import requests
import json
import pandas as pd
from sqlalchemy import create_engine, text, String, Float, DateTime, Integer

# %% 数据库连接配置
# 从patient-info-upload.py中参考的数据库配置
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

# %% 从数据库获取mrn列表
try:
    with engine.connect() as conn:
        # 从patient_admission_record表中获取所有mrn值
        mrn_list = pd.read_sql(
            "SELECT DISTINCT mrn FROM patient_admission_record", conn
        )["mrn"].tolist()

        # 删除mrn中重复的项目
        mrn_list = list(set(mrn_list))

        # 修复打印语句，显示正确的记录数量
        print(f"成功获取{len(mrn_list)}条不重复的mrn记录")
except Exception as e:
    print(f"从数据库获取mrn时出错: {e}")
    mrn_list = []


# %% 请求配置
url = "http://192.51.2.21/hospital/NursingAssessmentService/GetTextModel"

# 准备基本payload结构，后续会动态修改mrn字段
base_payload = {
    "serviceFunCode": "00000598",
    "serviceParam": {
        "type": "5",
        "tab_status": "tab1",
        "mrn": "",  # 将在循环中动态设置
        "series": "14",
        "timeflag": 0,
        "reptype": 4,
        "bltimeflag": 0,
    },
    "logInfo": {
        "Stay": "",
        "loginHosCodeNm": "庆春院区",
        "loginHospitalNm": "浙江大学医学院附属邵逸夫医院",
        "loginUserId": "73298",
        "loginUserNm": "董志怀",
        "loginHosCode": "A001",
        "loginDeptId": "33",
        "loginDeptNm": "耳鼻咽喉头颈外科",
        "loginPassword": "Dd73298",
        "loginDpower": "Y",
        "loginNpower": "",
        "loginStay": "O",
        "loginSysId": "4",
        "loginSysNm": "门诊医生系统",
        "Title": "3",
        "Zc": "ZC03",
        "loginBaseFlag": "",
        "loginBaseZyFlag": "",
        "loginSpecial": "0",
        "loginDoMain": "F",
        "loginIp": "20.117.1.198",
        "loginCa": "330623198212060014",
        "YSQX": True,
        "ATTENDING": "",
        "SsoToken": "SnJPTEZEZlR3ejJBYjNGVHVTODFQSFowOERER0Q0NjRVQlNBOVYrZVBFUnZHS2RrR3VZMGo0R0NnTFRWMjNBVGIyZVY3d091dW9SZkFJeDVwRHlMeEtOVCtkdUhFaEVRLzc3Y3VjZG50My96andWdlhXV1U0MDBtSkdFWlA5S1o4RUVOYXVZTEtQQmlwUE9oL0RTdGplVDgvVEJBR0s3VmhHMkhzN29VWUtBPQ==",
        "caflag": True,
        "castatus": "0",
        "CAAuthTime": 720,
        "CAAuthKEY": "29a8317e5cae401a8004b20bf92a8977",
        "CAGetAccessToken": "87e4e926ec644f33976fbe89ecd96730_13",
        "domain": "F",
        "DrId": "",
        "loginClincRoom": "",
        "loginClassId": "0",
        "loginCallQid": "026",
        "loginCallDate": "20250915",
        "loginCallAmPm": "AM",
        "LOGINEMPNETPHONE": "664628",
        "LOGINEMPNETPHONE2": "",
        "CELLPHONE": "13515818082",
        "Ip": "20.117.1.198",
        "ComputerName": "20.117.1.198",
        "doctorDept": "1",
        "loginBrlx": "NOR",
        "loginMedGroup": "30259",
        "loginMedGroupDeptId": "33",
        "isHemodialysis": False,
        "deptHemodialysis": "30",
        "alertMessage": "",
        "FLAG_ANTI": "2",
        "authEndTime": "2025-09-15 23:25:29",
        "GJBM": "D330104050866",
    },
}

headers = {
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lIjoiNzMyOTgiLCJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9naXZlbm5hbWUiOiLokaPlv5fmgIAiLCJubiI6IkEwMDEiLCJpZCI6IjczMjk4IiwianRpIjoiRiAgIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9leHBpcmF0aW9uIjoiMTIvMjkvMjAyMyAwMToxOToyNyIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6IkYgICIsIm5iZiI6MTcwMzc3MzE2NywiZXhwIjoxNzAzNzgzOTY3LCJpc3MiOiJFbXJzV2ViLkFwaSIsImF1ZCI6IndyIn0.EEPOpH_gh0cJFkSPjNKKKATMXVG8Hw6R48fSevgkX64",
    "Host": "20.21.1.224:5537",
    "Origin": "http://20.21.1.224:5537",
    "Referer": "http://20.21.1.224:5537/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
}

# %% 循环处理每个mrn并收集数据
repo_df = pd.DataFrame()  # 创建空DataFrame用于保存结果

success_count = 0
fail_count = 0

for mrn in mrn_list:
    try:
        # 创建当前mrn的payload副本并设置mrn值
        payload = base_payload.copy()
        payload["serviceParam"]["mrn"] = str(mrn)  # 确保mrn是字符串类型

        # 发送请求
        print(f"正在处理mrn: {mrn}")
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload)
        ).json()

        # 检查响应是否包含resultJson
        if "resultJson" in response:
            result_data = response["resultJson"]

            # 筛选reptyep为ES和CD的记录
            if isinstance(result_data, list):
                # 筛选reptyep为ES和CD的记录
                es_records = [
                    record
                    for record in result_data
                    if record.get("reptype") in ["ES", "CD", "WGK"]
                ]

                # 创建要删除的项目列表
                items_to_remove = [
                    "肠镜",
                    "胰胆",
                    "胃镜",
                    "鼻内",
                    "鼻咽",
                    "位置平衡",
                    "超声",
                    "前庭",
                    "睡眠",
                    "呼气试验",
                    "动态",
                    "吸入物",
                    "支气管",
                    "探查",
                    "中耳测试",
                ]

                filtered_records = []
                for record in es_records:
                    # 检查record中是否有checkitem字段，并且该字段不包含在删除列表中
                    if "checkitem" in record and isinstance(record["checkitem"], str):
                        # 检查checkitem是否包含任何要删除的项目
                        if not any(
                            item in record["checkitem"] for item in items_to_remove
                        ):
                            filtered_records.append(record)
                    else:
                        # 如果没有checkitem字段或者不是字符串类型，保留该记录
                        filtered_records.append(record)

                # 将过滤后的记录添加到结果DataFrame
                if filtered_records:
                    es_df = pd.DataFrame(filtered_records)
                    # 添加mrn列以便追踪来源
                    es_df["mrn"] = mrn
                    repo_df = pd.concat([repo_df, es_df], ignore_index=True)
                    success_count += 1
                    print(f"  成功获取{mrn}的ES记录，共{len(filtered_records)}条")
                else:
                    print(f"  {mrn}没有找到符合条件的记录")
            else:
                print(f"  {mrn}的响应结果不是预期的列表格式")
        else:
            print(f"  {mrn}的响应中未找到resultJson字段")

    except Exception as e:
        print(f"  处理{mrn}时出错: {e}")
        fail_count += 1

# %% 保存结果

if not repo_df.empty:
    print(f"\n处理完成！成功: {success_count}条, 失败: {fail_count}条")
    print(f"总共收集到{len(repo_df)}条reptyep为ES的记录")

    # 筛选指定的列
    selected_columns = ["repo", "repdr", "checkitem", "repdate", "series", "mrn"]
    # 获取实际存在的列
    existing_columns = [col for col in selected_columns if col in repo_df.columns]
    # 筛选数据
    filtered_repo_df = repo_df[existing_columns].copy()

    # 数据类型转换
    # 将repdate列转换为日期格式
    filtered_repo_df["repdate"] = pd.to_datetime(
        filtered_repo_df["repdate"], errors="coerce"
    )

    # 筛选repdate大于2020年1月1日的记录
    filtered_repo_df = filtered_repo_df[filtered_repo_df["repdate"] > "2020-01-01"]

    # 将checkitem列中的"|"替换为"-"
    filtered_repo_df["checkitem"] = filtered_repo_df["checkitem"].str.replace(
        "|", "-", regex=False
    )

    # 打印结果预览
    print("\n筛选后的结果预览:")
    print(filtered_repo_df.head())

    # %% 上传到数据库
    try:
        # 确保所有列都存在于DataFrame中
        required_columns = [
            "repo",
            "repdr",
            "checkitem",
            "repdate",
            "series",
            "mrn",
        ]

        # 数据类型转换
        # 将repdate列转换为日期格式
        filtered_repo_df["repdate"] = pd.to_datetime(
            filtered_repo_df["repdate"], errors="coerce"
        )

        dtype_mapping = {
            "repo": String(50),
            "repdr": String(50),
            "checkitem": String(255),
            "repdate": DateTime(),
            "series": String(20),
            "mrn": String(50),
            "name": String(50),
            "picdir": String(255),
        }

        # 上传数据到examination_record表
        with engine.connect() as conn:
            try:
                # 检查表是否存在，如果不存在则创建
                # 添加主键约束
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS examination_record (
                        "repo" VARCHAR(50) PRIMARY KEY,
                        "repdr" VARCHAR(50),
                        "checkitem" VARCHAR(255),
                        "repdate" DATE,
                        "series" VARCHAR(20),
                        "mrn" VARCHAR(50),
                        "name" VARCHAR(50),
                        "picdir" VARCHAR(255)
                    )
                    """
                    )
                )
                conn.commit()
            except Exception as e:
                print(f"创建表时出错: {e}")
                conn.rollback()

        # 获取现有记录的repo值以避免重复
        existing_repo = []
        try:
            with engine.connect() as conn:
                existing_repo = pd.read_sql(
                    "SELECT repo FROM examination_record", conn
                )["repo"].tolist()
        except Exception as e:
            print(f"查询现有repo记录时出错: {e}")

        # 筛选新数据（不在现有记录中）
        new_data = filtered_repo_df[
            ~filtered_repo_df["repo"].isin(existing_repo)
        ].copy()

        if not new_data.empty:
            # 上传数据
            new_data.to_sql(
                name="examination_record",
                con=engine,
                if_exists="append",
                index=False,
                dtype=dtype_mapping,
                method="multi",
            )
            print(f"\n成功上传{len(new_data)}条记录到数据库examination_record表")

            # 验证上传结果
            with engine.connect() as conn:
                total_count = pd.read_sql(
                    "SELECT COUNT(*) FROM examination_record", conn
                ).iloc[0, 0]
                print(f"数据库表examination_record中现有 {total_count} 条记录")
        else:
            print("\n没有新的记录需要上传到数据库，所有记录都已存在")
    except Exception as e:
        print(f"\n上传数据到数据库时出错: {e}")

# %%


# %%
# 下载 examination_record 表到 examination_record.csv 中
try:
    print("\n开始从数据库下载examination_record表...")
    # 使用现有的数据库连接引擎读取表数据
    with engine.connect() as conn:
        # 读取整个examination_record表
        examination_df = pd.read_sql_table("examination_record", conn)

        # 保存到CSV文件
        examination_df[examination_df["isLocalImageExist"] == "false"].to_csv(
            "examination_record.csv", index=False, encoding="utf-8-sig"
        )

        print(
            f"成功下载{len(examination_df[examination_df['isLocalImageExist'] == 'false'])}条记录到examination_record.csv文件"
        )
except Exception as e:
    print(f"下载examination_record表时出错: {e}")

# %%
