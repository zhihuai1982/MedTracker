# %%
import requests
import datetime
import pandas as pd

# 新增两周前后的日期变量
two_weeks_ago_str = (datetime.date.today() - datetime.timedelta(days=14)).strftime(
    "%Y-%m-%d"
)
two_weeks_later_str = (datetime.date.today() + datetime.timedelta(days=14)).strftime(
    "%Y-%m-%d"
)


reserve_list = requests.get(
    f"http://20.21.1.224:5537/api/api/Public/GetCadippatientnoticelist/1/{two_weeks_ago_str}/{two_weeks_later_str}/5/33A/"
).json()

hospitalized_list = requests.get(
    f"http://20.21.1.224:5537/api/api/Public/GetCadippatientnoticelist/1/{two_weeks_ago_str}/{two_weeks_later_str}/7/33A/"
).json()
# %%

# 合并两个列表并转换为DataFrame
combined_list = reserve_list + hospitalized_list
combined_df = pd.DataFrame(combined_list)[
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
        "arrangedate",
        "dohoscode",
        "PatientPhone",
    ]
]

# 删除NoticeFlag为"取消"的行
combined_df = combined_df[combined_df["NoticeFlag"] != "取消"]


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
combined_df["Attending"] = combined_df["Attending"].astype(str).map(name_mapping)
combined_df["Doctor"] = combined_df["Doctor"].astype(str).map(name_mapping)

# %%
# ... existing code ...

# 修改统计逻辑为分层统计
attending_stats = combined_df.groupby("Attending")
output = []
for attending, group in attending_stats:
    output.append(f"【{attending}】")

    # 先统计医生总数
    doctor_total = group.groupby("Doctor").size()
    # 再统计每个医生的诊断分布
    doctor_diag = group.groupby(["Doctor", "Diagnose"]).size()

    for doctor in doctor_total.index:
        # 输出医生总数
        output.append(f"{doctor}-{doctor_total[doctor]}")
        # 输出该医生的诊断分布
        diag_counts = doctor_diag.xs(doctor, level="Doctor")
        for diag, count in diag_counts.items():
            output.append(f"*********{diag} - {count}")

print("\n".join(output))

# %%
