# %%
import requests
import re
import json
import base64
import pandas as pd
import datetime


# %%

pContent = ""  # 选择要发布的内容，drgs或appointment

# %%
# 新增两周前后的日期变量
two_weeks_ago_str = (datetime.date.today() - datetime.timedelta(days=14)).strftime(
    "%Y-%m-%d"
)
two_weeks_later_str = (datetime.date.today() + datetime.timedelta(days=14)).strftime(
    "%Y-%m-%d"
)


appointment_patients = requests.get(
    f"http://20.21.1.224:5537/api/api/Public/GetCadippatientnoticelist/1/{two_weeks_ago_str}/{two_weeks_later_str}/5/33A/"
).json()

inpatient_patients = requests.get(
    f"http://20.21.1.224:5537/api/api/Public/GetCadippatientnoticelist/1/{two_weeks_ago_str}/{two_weeks_later_str}/7/33A/"
).json()
# %%

# 合并两个列表并转换为DataFrame
combined_list = appointment_patients + inpatient_patients
patient_df = pd.DataFrame(combined_list)[
    [
        "PatientName",
        "PatientID",
        "Isroom",
        "Diagnose",
        "drremark",
        "PatientSex",
        "PatientAge",
        "Attending",
        "Doctor",
        "NoticeFlag",
        "noticeRecord",
        "AppointmentIn",
        "AppOperativeDate",
        "ApplicationDate",
        "arrangedate",
        "dohoscode",
        "PatientPhone",
    ]
]

# 删除NoticeFlag为"取消"的行
patient_df = patient_df[patient_df["NoticeFlag"] != "取消"]


# %%

name_mapping = {
    "30042": "汤建国",
    "30044": "胡孙宏",
    "30046": "李文雅",
    "30047": "周明光",
    "30259": "肖芒",
    "30274": "邵瑾燕",
    "30291": "李旋",
    "30295": "姜晓华",
    "30346": "姜秀文",
    "30402": "张丹a",
    "30594": "张守德",
    "30705": "冯佳鹏",
    "30920": "帅冲",
    "30949": "周森浩",
    "31122": "党慧",
    "31123": "李洁",
    "31135": "金晟曦",
    "73062": "赵丽娜",
    "73145": "刘贝娜",
    "73272": "周国金",
    "73298": "董志怀",
    "73403": "齐杰",
    "73432": "潘虹c",
    "73498": "项轩",
    "73887": "岑威",
    "3X020": "张京娜",
    "3X051": "秦晨",
    "3X118": "盖寅哲",
    "3X217": "叶高飞",
    "3X218": "金茂",
    "3X236": "叶荆",
    "31231": "沈斌",
}

# 创建包含name_mapping中所有医生姓名的列表
doctor_names = list(name_mapping.values())

# 转换Attending和Doctor列为姓名
patient_df["Attending"] = patient_df["Attending"].astype(str).map(name_mapping)
# 使用 map 方法转换 Doctor 列，未匹配到的用原值填充
patient_df["Doctor"] = (
    patient_df["Doctor"].astype(str).map(name_mapping).fillna(patient_df["Doctor"])
)


# 修改统计逻辑为分层统计
attending_stats = patient_df.groupby("Attending")

# %%

pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'><br>每日预约病例</h1>\n<!-- /wp:heading -->\n"


# combined_df 中的 ApplicationDate 格式为"2025-03-17T08:11:44", 筛选出当天日期的行
today = datetime.date.today().strftime("%Y-%m-%d")
# today = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
today_patients = patient_df[patient_df["ApplicationDate"].str.startswith(today)]

# 使用today_rows代替combined_df进行当日统计
attending_stats_today = today_patients.groupby("Attending")
for attending, group in attending_stats_today:
    pContent += f"<br>================================<br>==  {attending}（{len(group)}）<br>================================<br><br>"

    # 统计逻辑保持相同结构
    doctor_counts = group.groupby("Doctor").size()
    diagnosis_counts = group.groupby(["Doctor", "Diagnose"]).size()

    for doctor in doctor_counts.index:
        pContent += f"<b>{doctor} - {doctor_counts[doctor]}</b><br>"
        diag_counts = diagnosis_counts.xs(doctor, level="Doctor")
        for diag, count in diag_counts.items():
            # 获取当前诊断下的患者姓名和病历号列表
            patient_info = group[
                (group["Doctor"] == doctor) & (group["Diagnose"] == diag)
            ][["PatientName", "PatientID"]]
            patient_list = ", ".join(
                [
                    f"{name}({id})"
                    for name, id in zip(
                        patient_info["PatientName"], patient_info["PatientID"]
                    )
                ]
            )
            pContent += f"┗ {diag} - {count}      【{patient_list}】<br>"


# %%
# 定义各院区的API端点
hospital_endpoints = {
    "庆春院区": f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/1/A001/{today}",
    "钱塘院区": f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77A/1/A002/{today}",
    "大运河院区": f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77F/1/A008/{today}",
    "绍兴院区": f"http://40.22.2.60:5537/api/api/Oper/GetOperArrange/77G/1/A009/{today}",
}

# 收集所有院区的手术安排数据
all_surgery_data = []

for hospital_name, endpoint in hospital_endpoints.items():
    try:
        response = requests.get(endpoint)
        if response.status_code == 200:
            surgery_data = response.json()
            # 为每条记录添加院区信息
            for record in surgery_data:
                record["hospital"] = hospital_name
            all_surgery_data.extend(surgery_data)
        else:
            print(f"获取{hospital_name}数据失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"获取{hospital_name}数据时出错: {e}")

# 将手术数据转换为DataFrame
if all_surgery_data:
    surgery_df = pd.DataFrame(all_surgery_data)

    # 提取需要的字段
    surgery_df = surgery_df[
        ["room", "cdo", "pname", "operp", "oper_statics", "mrn", "name", "hospital"]
    ]

    # 在这里添加新代码：通过mrn和PatientID匹配，将patient_df中的Doctor信息添加到surgery_df中
    # 创建一个映射字典，键为PatientID，值为Doctor
    # 为确保数据类型一致，将PatientID和mrn都转换为字符串类型
    patient_doctor_mapping = dict(
        zip(patient_df["PatientID"].astype(str), patient_df["Doctor"].astype(str))
    )

    # 将Doctor信息添加到surgery_df中，同样将mrn转换为字符串类型以确保匹配
    surgery_df["Doctor"] = (
        surgery_df["mrn"].astype(str).map(patient_doctor_mapping).fillna("未知")
    )

    # 筛选name列内容包含在doctor_names里的行
    surgery_filtered = surgery_df[surgery_df["name"].isin(doctor_names)]

    # 将筛选结果格式化输出到pContent
    if not surgery_filtered.empty:
        pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'><br>今日手术安排</h1>\n<!-- /wp:heading -->\n"

        # 按院区分组显示
        for hospital in surgery_filtered["hospital"].unique():
            hospital_data = surgery_filtered[surgery_filtered["hospital"] == hospital]
            pContent += f"<br>================================<br>==  {hospital}（{len(hospital_data)}台手术）<br>================================<br><br>"

            # 按医生分组显示
            for name in hospital_data["name"].unique():
                doctor_data = hospital_data[hospital_data["name"] == name]
                pContent += f"<b>{name} - {len(doctor_data)}台手术</b><br>"

                # 按room和cdo排序
                doctor_data = doctor_data.sort_values(["room", "cdo"])

                for _, row in doctor_data.iterrows():
                    pContent += f"┗ 【{row['room']}-{row['cdo']}】 {row['pname']} - {row['mrn']} - {row['Doctor']} <br> 手术: {row['operp']} - 状态: {row['oper_statics']}<br>"

                pContent += "<br>"
    else:
        pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'><br>今日手术安排</h1>\n<!-- /wp:heading -->\n"
        pContent += "<br>今日无手术安排<br><br>"


# %%
pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'><br>月度预约病例</h1>\n<!-- /wp:heading -->\n"


for attending, group in attending_stats:
    pContent += f"<br>================================<br>==  {attending}（{len(group)}）<br>================================<br><br>"

    # 先统计医生总数
    doctor_counts = group.groupby("Doctor").size()
    # 再统计每个医生的诊断分布
    diagnosis_counts = group.groupby(["Doctor", "Diagnose"]).size()

    # 修改循环为按数量降序输出
    for doctor in doctor_counts.sort_values(ascending=False).index:  # 新增排序
        # 输出医生总数
        pContent += f"<b>{doctor} - {doctor_counts[doctor]}</b><br>"
        # 输出该医生的诊断分布
        diag_counts = diagnosis_counts.xs(doctor, level="Doctor")
        for diag, count in diag_counts.items():
            pContent += f"┗ {diag} - {count}<br>"


# %%
# 新增WordPress发布模块
import json
import base64
from datetime import datetime

# WordPress认证信息
user = "zhihuai1982"
password = "NOqs cD6c 4Syt uCOf kLoU hjlm"
credentials = user + ":" + password
token = base64.b64encode(credentials.encode())
header = {"Authorization": "Basic " + token.decode("utf-8")}

# 读取/更新文章ID
try:
    with open("response_dailyreport.json", "r") as f:
        jsondata = json.load(f)
        today_post_id = (
            jsondata.get("id")
            if jsondata.get("modified").startswith(
                datetime.today().strftime("%Y-%m-%d")
            )
            else ""
        )
except Exception as e:
    today_post_id = ""

# 发布到WordPress
post_url = (
    f"https://wordpress.digitalnomad.host:1501/wp-json/wp/v2/posts/{today_post_id}"
)
post_data = {
    "title": f"Daily Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "status": "publish",
    "content": pContent,
}

response = requests.post(post_url, headers=header, json=post_data, verify=False)

# 保存响应信息
if response.status_code in [200, 201]:
    with open("response_dailyreport.json", "w") as f:
        json.dump(
            {
                "id": response.json().get("id"),
                "modified": response.json().get("modified"),
            },
            f,
        )

# %%
