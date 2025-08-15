# %%

import datetime
import requests  # 新增请求库
import pandas as pd  # 新增pandas库
from dateutil.relativedelta import relativedelta


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"
}


# %%
# 导入 level2-4.csv
level_df = pd.read_csv("level2-4.csv")

# %%

# 计算本月的周六日期
today = datetime.date.today()
first_day = today.replace(day=1)
next_month = first_day + relativedelta(months=1)
last_day = next_month - datetime.timedelta(days=1)

saturdays = []
current_day = first_day
while current_day <= last_day:
    if current_day.weekday() == 5:  # 5代表周六（周一=0）
        saturdays.append(current_day.strftime("%Y-%m-%d"))
    current_day += datetime.timedelta(days=1)

# === 新增数据获取部分 ===
all_data = []

# 原数据获取循环（约50-91行）
for saturday_date in saturdays:
    url = (
        f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/5/A001/{saturday_date}"
    )
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # 为每条数据添加周六日期标识
            for item in data:
                item["saturday_date"] = saturday_date
            all_data.extend(data)
        else:
            print(f"请求失败：{saturday_date}，状态码：{response.status_code}")
    except Exception as e:
        print(f"请求异常：{saturday_date}，错误信息：{str(e)}")

# 创建DataFrame
df = pd.DataFrame(all_data)

# === 新增筛选代码 ===
# 筛选姓名为董志怀的记录
dong_df = df[df["name"] == "董志怀"]

pContent = ""  # 选择要发布的内容，drgs或appointment

pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>DRGS 数据</h1>\n<!-- /wp:heading -->\n"


# 在循环开始前添加汇总数据结构
summary_data = []

for index, row in dong_df.iterrows():
    # 获取病历文书列表
    # http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/{mrn}/{series}/emr

    print(row["mrn"])

    # 通过 http://192.1.3.210/api/drg/thd/v1/patientInfoDetail?pid=row["mrn"]-row["series"]-&pageSourceType=THD&hosCode=A002 接口获取患者信息
    patientInfo = requests.get(
        f"http://192.1.3.210/api/drg/thd/v1/patientInfoDetail?pid={row['mrn']}-{row['series']}-&pageSourceType=THD&hosCode=A002",
        headers=headers,
    ).json()  # 添加.json()将响应转换为字典

    # 获取 patientInfo 中
    pContent += f"<!-- wp:heading --><br><h2 class='wp-block-heading' id = '{row['pname']}'>{
        row['pname']}</h2><br><!-- /wp:heading --><br>"

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

    # 替换 surgery_levels 列表为 DataFrame
    surgery_levels_df = pd.DataFrame(columns=["手术名称", "等级"])

    main_surgery = (
        surgery_detail.get("mainSurgery", {})
        if isinstance(surgery_detail, dict)
        else {}
    )
    surgery_name = (
        main_surgery.get("surgeryName", "") if isinstance(main_surgery, dict) else ""
    )

    if surgery_name:
        main_matches = level_df[
            level_df["手术名称"].str.contains(surgery_name, na=False, regex=False)
        ]
        if not main_matches.empty:
            surgery_levels_df = pd.concat(
                [
                    surgery_levels_df,
                    main_matches[["手术名称", "手术等级"]].rename(
                        columns={"手术等级": "等级"}
                    ),
                ]
            )
            pContent += f"<b>手术：</b>{surgery_name}————{main_matches[['手术等级']].values[0]}<br>"

    # 遍历次要手术列表（修复None类型不可迭代问题）
    second_surgeries = (
        surgery_detail.get("secondSurgeryList") or []  # 添加or []处理None情况
        if isinstance(surgery_detail, dict)
        else []
    )
    for surgery in second_surgeries:
        surgery_name = (
            surgery.get("surgeryName", "") if isinstance(surgery, dict) else ""
        )
        if surgery_name:
            sec_matches = level_df[
                level_df["手术名称"].str.contains(surgery_name, na=False, regex=False)
            ]
            if not sec_matches.empty:
                surgery_levels_df = pd.concat(
                    [
                        surgery_levels_df,
                        sec_matches[["手术名称", "手术等级"]].rename(
                            columns={"手术等级": "等级"}
                        ),
                    ]
                )
                pContent += (
                    f"┗{surgery_name}————{sec_matches[['手术等级']].values[0]}<br>"
                )

    # 获取最高等级手术信息
    if not surgery_levels_df.empty:
        max_row = surgery_levels_df.sort_values("等级", ascending=False).iloc[0]
        max_surgery_level = max_row["等级"]
        max_surgery_name = max_row["手术名称"]
    else:
        max_surgery_level = ""
        max_surgery_name = ""

    # 同样修复次要诊断部分的遍历（添加or []）
    second_diagnoses = (
        patientInfo.get("data", {}).get("diagnosisDetail", {}).get("secondDiagnosis")
        or []  # 添加or []处理None情况
    )
    for diagnosis in second_diagnoses:
        diagnosis_name = diagnosis.get("diagnosisName")
        if diagnosis_name:
            pContent += f"┗{diagnosis_name}<br>"

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
        "病历号": row["mrn"],
        "姓名": row["pname"],
        "诊断": diagnosis_name,
        "max手术名称": max_surgery_name,
        "max手术级别": max_surgery_level,
        "医疗总费用": 0,
        "DRG倍率": 0,
        "预计结余": 0,
        "手术费用": surgery_cost,
        "saturday_date": row["saturday_date"],  # 新增周六日期字段
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
# 原总表生成代码（约279行）
# if summary_data:
#     pContent += "<br><table style='border-collapse: collapse; width: 100%;'>"
#     pContent += "<tr style='background-color: #f2f2f2;'><th>病历号</th><th>姓名</th><th>诊断</th><th>max手术名称</th><th>max手术级别</th><th>总费用</th><th>DRG倍率</th><th>预计结余</th><th>手术费</th></tr>"

# 修改为按周六分组生成子表
from collections import defaultdict

weekly_groups = defaultdict(list)
for entry in summary_data:
    weekly_groups[entry["saturday_date"]].append(entry)

# 生成每周六分表
for saturday, entries in weekly_groups.items():
    pContent += f"<br><h2>{saturday} 周汇总表</h2>"
    pContent += "<table style='border-collapse: collapse; width: 100%;'>"
    pContent += "<tr style='background-color: #f2f2f2;'><th>病历号</th><th>姓名</th><th>诊断</th><th>max手术名称</th><th>max手术级别</th><th>总费用</th><th>DRG倍率</th><th>预计结余</th><th>手术费</th></tr>"

    # 周汇总统计
    weekly_total_medical = sum(
        float(e["医疗总费用"]) for e in entries if e["医疗总费用"]
    )
    weekly_total_profit = sum(e["预计结余"] for e in entries)
    weekly_total_surgery = sum(e["手术费用"] for e in entries)

    for entry in entries:
        # 根据倍率值设置行背景色
        bg_color = (
            "#ffcccc"
            if (float(entry["DRG倍率"]) < 0.4 or float(entry["DRG倍率"]) > 1)
            else ""
        )
        pContent += f"<tr style='background-color: {bg_color}'>"
        pContent += (
            f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['病历号']}</td>"
        )
        pContent += (
            f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['姓名']}</td>"
        )
        pContent += (
            f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['诊断']}</td>"
        )
        pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['max手术名称']}</td>"
        pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['max手术级别']}</td>"
        pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['医疗总费用']}</td>"
        pContent += (
            f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['DRG倍率']}</td>"
        )
        pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['预计结余']}</td>"
        pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['手术费用']}</td>"
        pContent += f"</tr>"

    # 添加周汇总行
    pContent += "<tr style='background-color: #e6e6e6; font-weight: bold;'>"
    pContent += (
        "<td colspan='5' style='border: 1px solid #ddd; padding: 8px;'>本周汇总</td>"
    )
    pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{weekly_total_medical:.2f}</td>"
    pContent += "<td style='border: 1px solid #ddd; padding: 8px;'>-</td>"
    pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{weekly_total_profit:.2f}</td>"
    pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{weekly_total_surgery:.2f}</td>"
    pContent += "</tr>"
    pContent += "</table><br>"

# 生成最终总汇总表
pContent += "<br><h2>全月总汇总表</h2>"
pContent += "<table style='border-collapse: collapse; width: 100%;'>"
pContent += "<tr style='background-color: #f2f2f2;'><th>病历号</th><th>姓名</th><th>诊断</th><th>max手术名称</th><th>max手术级别</th><th>总费用</th><th>DRG倍率</th><th>预计结余</th><th>手术费</th></tr>"

for entry in summary_data:  # 取最近添加的数据
    # 根据倍率值设置行背景色
    bg_color = (
        "#ffcccc"
        if (float(entry["DRG倍率"]) < 0.4 or float(entry["DRG倍率"]) > 1)
        else ""
    )
    pContent += f"<tr style='background-color: {bg_color}'>"
    pContent += (
        f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['病历号']}</td>"
    )
    pContent += (
        f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['姓名']}</td>"
    )
    pContent += (
        f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['诊断']}</td>"
    )
    pContent += (
        f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['max手术名称']}</td>"
    )
    pContent += (
        f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['max手术级别']}</td>"
    )
    pContent += (
        f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['医疗总费用']}</td>"
    )
    pContent += (
        f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['DRG倍率']}</td>"
    )
    pContent += (
        f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['预计结余']}</td>"
    )
    pContent += (
        f"<td style='border: 1px solid #ddd; padding: 8px;'>{entry['手术费用']}</td>"
    )
    pContent += f"</tr>"

    # 添加汇总行
    total_medical = sum(
        float(entry["医疗总费用"]) for entry in summary_data if entry["医疗总费用"]
    )
    total_profit = sum(entry["预计结余"] for entry in summary_data)
    total_surgery = sum(entry["手术费用"] for entry in summary_data)

pContent += "<tr style='background-color: #e6e6e6; font-weight: bold;'>"
pContent += "<td style='border: 1px solid #ddd; padding: 8px;' colspan='5'>汇总</td>"
pContent += (
    f"<td style='border: 1px solid #ddd; padding: 8px;'>{total_medical:.2f}</td>"
)
pContent += "<td style='border: 1px solid #ddd; padding: 8px;'>-</td>"
pContent += f"<td style='border: 1px solid #ddd; padding: 8px;'>{total_profit:.2f}</td>"
pContent += (
    f"<td style='border: 1px solid #ddd; padding: 8px;'>{total_surgery:.2f}</td>"
)
pContent += "</tr>"

pContent += "</table><br>"


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
    with open("saturday-plus.json", "r") as f:
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
    "title": f"Saturday Plus - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "status": "publish",
    "content": pContent,
}

response = requests.post(post_url, headers=header, json=post_data, verify=False)

# 保存响应信息
if response.status_code in [200, 201]:
    with open("saturday-plus.json", "w") as f:
        json.dump(
            {
                "id": response.json().get("id"),
                "modified": response.json().get("modified"),
            },
            f,
        )
