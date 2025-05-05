# %%
import requests
import re
import json
import base64
import pandas as pd
import datetime

# 导入 functions.py
from functions import *

# %%
# trello

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"
}

query = {
    "key": "f45b896485c79fe922e7f022a8bc6f71",
    "token": "ATTAae59e22e7d144839c54a444aa4f24d4f3ede09405b11ace472e773a78a23b0e8F2D629A2",
}

trelloheaders = {"Accept": "application/json"}

# %%
# trello上获取患者住院号列表和id列表，并排除其他无关列表

tpListRaw = requests.request(
    "GET",
    "https://api.trello.com/1/boards/67c42e00d9ad2ce5d8876f0b/lists",
    headers=trelloheaders,
    params=query,
    verify=False,
).json()

pattern = r"^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-.*$"

tpList = [
    {key: d[key] for key in ["id", "name"]}
    for d in tpListRaw
    if re.match(pattern, d["name"])
]
for item in tpList:
    item["mrn"] = int(item["name"].split("-")[2])
    item["tdiag"] = item["name"].split("-")[3]

# %%  住院系统获取患者列表

# 获取患者列表，得到住院号mrn和series
# http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30046/33A/A002

hpListRaw = requests.get(
    "http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30047/33A/A002",
    headers=headers,
).json()

hpList = [
    {key: d[key] for key in ["bedid", "pname", "mrn", "series", "diag", "admdays"]}
    for d in hpListRaw
]

# # hpList 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天
# for item in hpList:
#     item['h2name'] = f"{item['bedid']}-{item['pname']
#                                         }-{item['mrn']}-{item['admdays']}d-{item['diag']}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"
}

# %%
#  根据mrn列合并hpList和tplist，保存到pList，要求保存hpList中的所有行，tplist中的id列
pList = pd.merge(pd.DataFrame(hpList), pd.DataFrame(tpList), on="mrn", how="left")

# 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天-tdiag
pList["h2name"] = (
    pList["bedid"].astype(str)
    + "-"
    + pList["pname"]
    + "-"
    + pList["admdays"].astype(str)
    + "d-"
    + pList["tdiag"]
    + "-"
    + pList["mrn"].astype(str)
)

# pList 根据  bedid 列逆序排列
# pList = pList.sort_values(by="bedid", ascending=True)


# 自定义排序规则（W后>90的按升序排在前面）
def create_sort_key(bedid):
    try:
        prefix, suffix = bedid.split("W")
        suffix_num = int(suffix)
        # 返回元组：前缀 | 是否>90（反向排序） | 实际数值
        return (prefix + "W", -int(suffix_num > 90), suffix_num)
    except:
        return (bedid, 0, 0)


pList["sort_key"] = pList["bedid"].apply(create_sort_key)
pList = pList.sort_values(by="sort_key").drop(columns=["sort_key"])

# print(pList)

# pList 删除 mrn 为s 33565 的行
# pList = pList[pList['mrn'] != 4009984]

# pList = pList.iloc[:1]

# %%

pContent = ""  # 选择要发布的内容，drgs或appointment

pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>DRGS 数据</h1>\n<!-- /wp:heading -->\n"


# 在循环开始前添加汇总数据结构
summary_data = []

for index, row in pList.iterrows():
    # 获取病历文书列表
    # http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/{mrn}/{series}/emr

    print(row["mrn"])

    # 通过 http://192.1.3.210/api/drg/thd/v1/patientInfoDetail?pid=row["mrn"]-row["series"]-&pageSourceType=THD&hosCode=A002 接口获取患者信息
    patientInfo = requests.get(
        f"http://192.1.3.210/api/drg/thd/v1/patientInfoDetail?pid={row['mrn']}-{row['series']}-&pageSourceType=THD&hosCode=A002",
        headers=headers,
    ).json()  # 添加.json()将响应转换为字典

    # 获取 patientInfo 中
    pContent += f"<!-- wp:heading --><br><h2 class='wp-block-heading' id = '{row['h2name']}'>{
        row['h2name']}</h2><br><!-- /wp:heading --><br>"

    # 诊断
    diagnosis_name = (
        patientInfo.get("data", {})
        .get("diagnosisDetail", {})
        .get("mainDiagnosis", {})
        .get("diagnosisName", "")
    )
    if diagnosis_name:
        pContent += f"<b>诊断：</b><br>{diagnosis_name}<br>"

    # 遍历次要诊断列表
    second_surgeries = (
        patientInfo.get("data", {})
        .get("diagnosisDetail", {})
        .get("secondDiagnosis", [])
    )
    for diagnosis in second_surgeries:  # 即使列表不存在/为空也能安全遍历
        diagnosis_name = diagnosis.get("diagnosisName")
        if diagnosis_name:  # 过滤空值
            pContent += f"┗{diagnosis_name}<br>"  # 添加标识前缀

    # 手术名称

    # 添加类型检查确保对象是字典
    surgery_detail = patientInfo.get("data", {}) or {}
    surgery_detail = (
        surgery_detail.get("surgeryDetail", {})
        if isinstance(surgery_detail, dict)
        else {}
    )

    main_surgery = (
        surgery_detail.get("mainSurgery", {})
        if isinstance(surgery_detail, dict)
        else {}
    )
    surgery_name = (
        main_surgery.get("surgeryName", "") if isinstance(main_surgery, dict) else ""
    )
    if surgery_name:
        pContent += f"<b>手术：</b><br>{surgery_name}<br>"

    # 遍历次要手术列表
    second_surgeries = (
        surgery_detail.get("secondSurgeryList", [])
        if isinstance(surgery_detail, dict)
        else []
    )
    for surgery in second_surgeries:

        surgery_name = (
            surgery.get("surgeryName", "") if isinstance(surgery, dict) else ""
        )
        if surgery_name:
            pContent += f"┗{surgery_name}<br>"

    # DRGS 数据
    forecasts = patientInfo.get("data", {}).get("forecastInfoList", [])
    for forecast in forecasts:
        magnification = forecast.get("magnification", 0)
        magnification_text = f"倍率：{magnification}"

        # 根据倍率值调整样式
        if magnification < 0.4 or magnification > 1:
            magnification_text = f"<span style='color:red; font-weight:bold; font-size:larger;'>{magnification_text}</span>"

        pContent += (
            f"<b>DRGS：</b><br>"
            f"drgCode：{forecast.get('drgCode', '')}<br>"
            f"DRG分组：{forecast.get('drgName', '')}<br>"
            f"医疗总费用：{forecast.get('ylzfy', '')}<br>"
            f"预计结算金额：{forecast.get('feeSettle', 0)}<br>"
            f"预计结余：{forecast.get('feeProfit', 0)}<br>"
            f"类型：{forecast.get('caseTypeName', '')}<br>"
            f"{magnification_text}<br><br>"
        )

    # 手术费用提取
    fee_items = patientInfo.get("data", {}).get("feeItemList", [])

    surgery_cost = 0
    for fee_item in fee_items:
        if fee_item.get("itemName", "") == "手术费":
            surgery_cost += int(fee_item.get("totalCost", 0))

    if surgery_cost:
        pContent += f"手术费总额：{surgery_cost} 元<br>"

    # 在获取手术费用后添加数据收集（在 surgery_cost 计算之后）
    summary_entry = {
        "床号": row["bedid"],
        "姓名": row["pname"],
        "诊断": row["tdiag"],
        "医疗总费用": 0,
        "DRG倍率": 0,
        "预计结余": 0,
        "手术费用": surgery_cost,
    }

    # 遍历 forecasts 获取 DRGS 数据
    forecasts = patientInfo.get("data", {}).get("forecastInfoList", [])
    for forecast in forecasts:
        # 更新每个 forecast 的数据到汇总表
        summary_entry.update(
            {
                "医疗总费用": forecast.get("ylzfy", ""),
                "DRG倍率": forecast.get("magnification", 0),
                "预计结余": forecast.get("feeProfit", 0),
            }
        )
        summary_data.append(summary_entry.copy())  # 使用副本避免数据覆盖

pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>DRGS 汇总表</h1>\n<!-- /wp:heading -->\n"

# 在 DRGS 数据显示后添加表格生成（在 surgery_cost 显示之后）
# 生成表格 HTML
if summary_data:
    pContent += "<br><table style='border-collapse: collapse; width: 100%;'>"
    pContent += "<tr style='background-color: #f2f2f2;'><th>床号</th><th>姓名</th><th>诊断</th><th>总费用</th><th>DRG倍率</th><th>预计结余</th><th>手术费</th></tr>"

    for entry in summary_data:  # 取最近添加的数据
        # 根据倍率值设置行背景色
        bg_color = (
            "#ffcccc"
            if (float(entry["DRG倍率"]) < 0.4 or float(entry["DRG倍率"]) > 1)
            else ""
        )
        pContent += f"<tr style='background-color: {bg_color}'>"
        pContent += (
            f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['床号']}</td>"
        )
        pContent += (
            f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['姓名']}</td>"
        )
        pContent += (
            f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['诊断']}</td>"
        )
        pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['医疗总费用']}</td>"
        pContent += (
            f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['DRG倍率']}</td>"
        )
        pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['预计结余']}</td>"
        pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['手术费用']}</td>"
        pContent += f"</tr>"

    pContent += "</table><br>"


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
}

# 转换Attending和Doctor列为姓名
patient_df["Attending"] = patient_df["Attending"].astype(str).map(name_mapping)
patient_df["Doctor"] = patient_df["Doctor"].astype(str).map(name_mapping)


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
            pContent += f"┗ {diag} - {count}<br>"

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
password = "dtPD 9emY eyH8 Vcbn nl31 WKMr"
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
