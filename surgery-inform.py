# %%
import requests
import re
import json
import base64
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta, MO
import xml.etree.ElementTree as ET

# from collections import defaultdict

pContent = ""

# 新增手术安排请求

# 生成今天日期字符串
today = datetime.datetime.today() + datetime.timedelta(days=0)
today_str = today.strftime("%Y-%m-%d")

# 生成最近的周一日期字符串
next_monday = datetime.date.today() + relativedelta(weekday=MO(0))
next_monday_str = next_monday.strftime("%Y-%m-%d")

oper_url = (
    f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/5/A001/{next_monday_str}"
)

url = "http://192.1.3.110:8080/Zqtys/GetModelListServlet"

headers = {
    "Host": "192.1.3.110:8080",
    "Origin": "http://192.1.3.110:8080",
    "Referer": "http://192.1.3.110:8080/Zqtys/main_pc/MainForm.jsp?modelhistory_rdn=421767669&mrn=10835009&name=%E9%A9%AC%E8%8D%A3%E6%9D%A5",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
}

try:
    oper_response = requests.get(oper_url)
    oper_response.encoding = "UTF-8"

    if oper_response.status_code == 200:
        oper_data = oper_response.json()
        oper_df = pd.DataFrame(oper_data)
        # print(oper_df)
        filtered_oper = oper_df[oper_df["name"] == "董志怀"]

        # 新增：创建整合表格
        combined_consents = []

        for index, row in filtered_oper.iterrows():
            # 动态更新请求参数
            dynamic_data = {
                "deptid": "33",
                "mrn": str(row["mrn"]),
                "series": str(row["series"]),
            }

            try:
                # 发送请求
                patient_response = requests.post(
                    url, headers=headers, data=dynamic_data
                )
                patient_response.encoding = "UTF-8"

                if patient_response.status_code == 200:
                    # 解析响应数据
                    root = ET.fromstring(patient_response.text)
                    consent_list = []

                    for item in root.findall(".//ALL"):
                        fields = [f for f in re.split(r"\|+", item.text) if f]
                        consent_list.append(
                            {
                                "姓名": row["pname"],
                                "病历号": row["mrn"],
                                "手术名称": row["operp"],
                                "文书名称": fields[0],
                                "工号": fields[1],
                                "签署日期": fields[2],
                                "序列号": fields[4],
                            }
                        )

                    # 合并数据
                    if consent_list:
                        combined_consents.extend(consent_list)

            except Exception as e:
                print(f"处理患者 {row['name']} 时发生错误: {str(e)}")

        # 打印整合后的表格
        if combined_consents:
            final_df = pd.DataFrame(combined_consents)

            # 筛选签署日期在最近3天内的记录
            three_days_ago = datetime.datetime.now() - datetime.timedelta(days=3)
            final_df["签署日期"] = pd.to_datetime(final_df["签署日期"])
            final_df = final_df[final_df["签署日期"] >= three_days_ago]

            # 将控制台输出转为HTML格式
            pContent += "\n<hr>\n<h2>患者知情同意书汇总表</h2>\n"
            pContent += (
                "<table border='1' style='border-collapse: collapse; width: 100%;'>\n"
            )

            # 按患者分组
            current_patient = None
            for _, row in final_df.sort_values(["病历号", "签署日期"]).iterrows():
                # 患者信息行（淡藍色背景）
                if current_patient != (row["姓名"], row["病历号"], row["手术名称"]):
                    current_patient = (row["姓名"], row["病历号"], row["手术名称"])
                    patient_info = (
                        f"{row['姓名']}（病历号：{row['病历号']}） - {row['手术名称']}"
                    )
                    pContent += f"<tr style='background-color: #e6f3ff;'>"
                    pContent += (
                        f"<td colspan='2'><strong>{patient_info}</strong></td></tr>\n"
                    )

                # 文书信息行
                bg_color = (
                    "#ffe5e5"
                    if "术知情同意书" in row["文书名称"]
                    else "#e5ffe5" if "患者知情选择书" in row["文书名称"] else "#ffffff"
                )
                pContent += f"<tr style='background-color: {bg_color}'>"
                pContent += f"<td style='padding-left: 30px'>{row['文书名称']}</td>"
                pContent += f"<td>{row['签署日期']}</td></tr>\n"

            pContent += "</table>"
        else:
            pContent += "\n<p>未找到符合条件的知情同意书数据</p>"

    else:
        print(f"手术安排请求失败，状态码：{oper_response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"手术安排请求异常：{str(e)}")

# %% 新入院患者API请求
admission_url = f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{today_str}/{next_monday_str}/7/33/30044/"
admission_response = requests.get(admission_url)
admission_data = admission_response.json()

# 创建入院患者DataFrame
admission_df = pd.DataFrame(admission_data)
admission_df["PatientID"] = admission_df["PatientID"].astype("int64")


# %%
# 手术知情同意书详情请求

# 筛选包含手术知情同意书的记录
surgical_consents = final_df[final_df["文书名称"].str.contains("术知情同意书")]

if not surgical_consents.empty:
    for _, row in surgical_consents.iterrows():
        detail_data = {"modelhistory_rdn": row["序列号"], "mrn": row["病历号"]}

        try:
            # 发送详情请求
            detail_response = requests.post(
                "http://192.1.3.110:8080/Zqtys/GetHistoryModelServlet",
                headers=headers,
                data=detail_data,
            )

            # 将控制台输出转为HTML格式
            pContent += f"\n<h2>手术知情同意书-{row['姓名']}-{row['病历号']}</h2>\n"

            pContent += f"\n手术名称（通知单）: {final_df[final_df['病历号'] == row['病历号']]['手术名称'].values[0] if not final_df[final_df['病历号'] == row['病历号']].empty else '未记录'}\n"

            pContent += f"\n医生备注: {admission_df[admission_df['PatientID'] == row['病历号']]['drremark'].values[0] if not admission_df[admission_df['PatientID'] == row['病历号']].empty else '无备注'}\n"

            if detail_response.status_code == 200:

                allowed_images = {
                    "患者签字": r"患者签字：(.*?)(?=日期)",
                }

                preserved_images = []
                for name, pattern in allowed_images.items():
                    matches = re.findall(pattern, detail_response.text, re.DOTALL)
                    if matches:
                        preserved_images.append(f"{name}: {matches[0].strip()}")

                images_content = "\n\n".join(preserved_images)

                cleaned_content = re.sub(
                    r'<input[^>]*?value\s*=\s*"([^"]*)"[^>]*>',
                    r"\1",
                    detail_response.text,
                    flags=re.IGNORECASE,
                )
                # 删除所有HTML标签（包括<br>）
                cleaned_content = re.sub(r"<[^>]+>", "", cleaned_content)

                # 原有清理逻辑
                cleaned_content = re.sub(r"&ensp;", "", cleaned_content)
                cleaned_content = re.sub(r"(\n){2,}", "\n", cleaned_content)
                cleaned_content = re.sub(r"(<br>)+", "", cleaned_content).strip("<br>")

                # print(cleaned_content)

                # 定义带名称的正则表达式字典
                allowed_patterns = {
                    "主诊医生": r"您的主诊医生是:(.*?)(?=\n|您)",
                    "经管医生": r"您的经管医生是:(.*?)(?=\n|$)",
                    "当前诊断": r"目前诊断:(.*?)(?=\n|$)",
                    "手术名称": r"拟施行的手术/操作名称:\n(.*?)(?=\n|$)",
                    "手术目的": r"预期的效果：\n(.*?)(?=\n|$)",
                    "术中风险": r"功能障碍  \n其它：(.*?)(?=\n)",
                    "术后风险": r"再次手术  \n其它：(.*?)(?=\n)",
                    "保守治疗": r"可供选择的其它治疗方法及您的选择：(.*?)(?=\n)",
                    "选择治疗": r"您选择：(.*?)(?=\n)",
                    "植入物": r"类型及厂家：\n(.*?)(?=\n|7)",
                    "主刀医生": r"主刀医生是：(.*?)(?=\n)",
                    "eql主诊医生": r"您的主诊医师：(.*?)(?=\n|；)",
                    "eql主刀医生": r"主刀医师：(.*?)(?=\n|；)",
                    "eql当前诊断": r"目前诊断：(.*?)(?=\n|$)",
                    "eql手术名称": r"拟行手术方案：(.*?)(?=\n|$)",
                    "eql选择治疗": r"您选择的手术方案：(.*?)(?=\n)",
                }

                preserved = []
                for name, pattern in allowed_patterns.items():
                    matches = re.findall(pattern, cleaned_content, re.DOTALL)
                    if matches:
                        preserved.append(f"{name}: {matches[0].strip()}")

                cleaned_content = "\n\n".join(preserved)

                pContent += f"<div class='response-content'>{cleaned_content}\n{images_content}</div>"

            else:
                pContent += f"\n<p style='color:red'>请求失败，状态码：{detail_response.status_code}</p>"

        except Exception as e:
            print(f"\n请求异常：{str(e)}")
else:
    print("\n未找到手术知情同意书记录")

# %%

# 患者知情选择书请求

# 筛选包含手术知情同意书的记录
author_content = final_df[final_df["文书名称"].str.contains("患者知情选择书")]

if not author_content.empty:
    for _, row in author_content.iterrows():
        detail_data = {"modelhistory_rdn": row["序列号"], "mrn": row["病历号"]}

        try:
            # 发送详情请求
            detail_response = requests.post(
                "http://192.1.3.110:8080/Zqtys/GetHistoryModelServlet",
                headers=headers,
                data=detail_data,
            )

            # 将控制台输出转为HTML格式
            pContent += f"\n<h2>患者知情选择书-{row['姓名']}-{row['病历号']}</h2>\n"

            # 原代码（保留其他处理逻辑）
            cleaned_content = re.sub(r"<(?!img\b)[^>]+>", "", detail_response.text)
            cleaned_content = re.sub(r"&ensp;", "", cleaned_content)

            # print(cleaned_content)

            if detail_response.status_code == 200:

                # 定义带名称的正则表达式字典
                allowed_patterns = {
                    "患者签名": r"患者签名：(.*?)(?=签字日期：  \n  )",
                    "患者授权签名": r"若产生不良后果将由本人承担。\n患者签名：(.*?)(?=签字日期： \n  以上内容由患者本人填写)",
                    "被授权人签名": r"被授权人签名：(.*?)(?=签字日期：)",
                    "关系": r"患者关系：(.*?)(?=\n)",
                }

                preserved = []
                for name, pattern in allowed_patterns.items():
                    matches = re.findall(pattern, cleaned_content, re.DOTALL)
                    if matches:
                        preserved.append(f"{name}: {matches[0].strip()}")

                cleaned_content = "\n\n".join(preserved)

                pContent += f"<div class='response-content'>{cleaned_content}</div>"

            else:
                pContent += f"\n<p style='color:red'>请求失败，状态码：{detail_response.status_code}</p>"

        except Exception as e:
            print(f"\n请求异常：{str(e)}")
else:
    print("\n未找到手术知情同意书记录")

# %%

# 将pContent中“左”的背景颜色改为红色，“右”的背景颜色改为绿色，文字改为白色，字号改为1.5倍

pContent = re.sub(
    r"左",
    r'<span style="background-color:red;color:white;font-size:1.5em">左</span>',
    pContent,
)

pContent = re.sub(
    r"右",
    r'<span style="background-color:#008000;color:white;font-size:1.5em">右</span>',
    pContent,
)

# print(pContent)


# %%
# https://robingeuens.com/blog/python-wordpress-api/

user = "zhihuai1982"
# password = "BSNz VB3W InRj LlFr ueKU 1ZSk"
password = "NOqs cD6c 4Syt uCOf kLoU hjlm"
credentials = user + ":" + password
token = base64.b64encode(credentials.encode())
header = {"Authorization": "Basic " + token.decode("utf-8")}

# 读取 response.json， 如果 modified 提供的日期和今天的日期相同，则把 id 信息保存到变量 todayPostID 里

# Load the data from the JSON file
with open("response_surgeryinform.json", "r") as f:
    jsondata = json.load(f)

# Get today's date as a string
today = datetime.datetime.now().strftime("%Y-%m-%d")

# Check if the 'modified' date in the data is today
if jsondata.get("modified").split("T")[0] == today:
    # If so, save the 'id' to the variable todayPostID
    todayPostID = jsondata.get("id")
else:
    todayPostID = ""

# todayPostID = ''
url = f"https://wordpress.digitalnomad.host:1501/wp-json/wp/v2/posts/{todayPostID}"
post = {
    "title": f"术前谈话 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    "status": "publish",
    "content": pContent,
}
response = requests.post(url, headers=header, json=post, verify=False)
print(response)

# %%

# Parse the response text as JSON
response_data = json.loads(response.text)

# Extract the id and date
data_to_save = {
    "id": response_data.get("id"),
    "date": response_data.get("date"),
    "modified": response_data.get("modified"),
}

# Save the data to a JSON file
with open("response_surgeryinform.json", "w") as f:
    json.dump(data_to_save, f)

# %%
