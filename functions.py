import re
import requests
import pandas as pd
from io import StringIO
import dateutil.relativedelta as rd
import datetime


# %%
# 根据住院号获得检查列表
def get_lab_results(mrn, duration):
    hLabList = requests.get(
        f"http://20.21.1.224:5537/api/api//LisReport/GetLisReportIndexHalf/{mrn}/1").json()

    # 根据hLabList里的dodate筛选出大于当前日期-duration（天）的数据
    hLabList = [item for item in hLabList if (
        pd.Timestamp.now() - pd.Timestamp(item['dodate'])).days <= duration]

    if not hLabList:
        return "No match found"

    totalLabRes = []
    for lab in hLabList:
        url = f"http://20.21.1.224:5537/api/api/LisReport/GetLisReportDetail/{mrn}/{lab['dodate']}/{lab['specimenid']}/{lab['domany']}"
        labRes = requests.get(url).json()
        for item in labRes:
            item['dodate'] = lab['dodate']
            item['checkitem'] = lab['checkitem']
        totalLabRes.extend(labRes)  # 将 labRes 的结果添加到 totalLabRes 列表中

    df = pd.DataFrame(totalLabRes)  # 将 totalLabRes 列表转换为 DataFrame
    df = df[['xmmc', 'jg', 'zdbz', 'ckqj', 'dodate', 'checkitem']]  # 选择需要的列

    def process_group(group):
        if group['zdbz'].replace('', pd.NA).isnull().all():  # 如果 'zdbz' 列都是空白
            return pd.DataFrame([{
                'xmmc': '',
                'jg': 'all阴性',
                'zdbz': '',
                'ckqj': '',
                'dodate': group['dodate'].iloc[0],
                'checkitem': group['checkitem'].iloc[0]
            }])
        else:
            # 删除 'zdbz' 为空白的行
            return group[group['zdbz'].replace('', pd.NA).notnull()]

    df = df.groupby('checkitem').apply(process_group).reset_index(drop=True)

    # 将df按照dodate由大到小逆向排序
    df = df.sort_values(by='dodate', ascending=False)
    # 将dodate转换成日期格式
    df['dodate'] = pd.to_datetime(df['dodate']).dt.strftime('%Y-%m-%d')

    # 创建一个字典，用于替换checkitem里的内容
    # 比如将 “ADA,CA,AST,ALP,GGT,MG,PHOS,CK,LDH,hsCRP,同型半胱氨,CysC,D3-H,NEFA,RBP,SAA,TBA,LP(a),*LDL,‖生化筛查”替换为“生化全套”
    checkitemDict = {
        "ADA,CA,AST,ALP,GGT,MG,PHOS,CK,LDH,hsCRP,同型半胱氨,CysC,D3-H,NEFA,RBP,SAA,TBA,LP(a),*LDL,‖生化筛查": "生化全套",
        "CBC,ABO输血,RH输血": "血常规",
        "HCVAb,HIVAb,梅毒筛选,AHBCIgM,前S抗原,乙肝定量": "术前免疫",
        "HBsAg快,HCVAb快,HIVAgAb,梅毒快,TRUST,梅毒TPPA": "日间免疫",
        "ABScreen,Rh表型CcEe": "血型"}
    # 利用字典替换checkitem列的内容
    df['checkitem'] = df['checkitem'].replace(checkitemDict)

    df.rename(columns={'xmmc': '项目名称', 'jg': '结果', 'zdbz': 'R',
              'ckqj': '参考范围', 'dodate': '检验日期', 'checkitem': '检验项目'}, inplace=True)

    # 定义一个函数，该函数会检查一个日期是否是今天的日期
    def highlight_today(row):
        if pd.to_datetime(row['检验日期']).date() == datetime.datetime.now().date():
            return ['background-color: yellow']*len(row)
        else:
            return ['']*len(row)

   # 创建一个包含重点检验结果名称的列表
    important_tests = ["血小板计数","白细胞计数","中性粒百分数","血红蛋白量","钾","钙","肌酐","葡萄糖",'尿素/肌酐','丙氨酸氨基转移酶','天冬氨酸氨基转移酶','白蛋白','超敏C反应蛋白','D-二聚体(D-Di)']

    # 定义一个函数，该函数检查一个值是否在重点检验结果名称列表中
    def highlight_important_tests(val):
        if val['项目名称'] in important_tests:
            return ['color: red']*len(val)
        else:
            return ['']*len(val)

    labStyles = [
        {'selector': 'th.col_heading.level0.col0',
            'props': [('width', '100px')]},
        {'selector': 'th.col_heading.level0.col1',
            'props': [('width', '80px')]},
        {'selector': 'th.col_heading.level0.col2',
            'props': [('width', '40px')]},
        {'selector': 'th.col_heading.level0.col3',
            'props': [('width', '150px')]},
        {'selector': 'th.col_heading.level0.col4',
            'props': [('width', '120px')]},
        {'selector': 'th.col_heading.level0.col5',
            'props': [('width', '110px')]}
    ]

    return df.style.set_table_styles(labStyles).hide().apply(highlight_important_tests, axis=1).apply(highlight_today, axis=1).to_html()

# df = get_lab_results(4878420, 30)
# print(df)

# %%


def get_exam_results(mrn, duration):
    # 根据住院号获取检查结果列表
    hExamList = requests.get(
        f"http://20.21.1.224:5537/api/api/LisReport/GetViewReportIndex/{mrn}/").json()

    # 筛选出hExamList中pacsType非空的字典
    hExamList = [d for d in hExamList if d['pacsType']]

    # print(hExamList)

    if not hExamList:
        return "No match found"

    # 根据hExamList里的repdate筛选出大于当前日期-duration（天）的数据
    hExamList = [item for item in hExamList if (
        pd.Timestamp.now() - pd.Timestamp(item['repdate'])).days <= duration]

    # 根据 hExamList 里的fromdb、repo项目，构建url，格式为 "http://20.21.1.224:5537/api/api/LisReport/Get{Exam['fromdb']}Detail/{mrn}/{Exam['repo']}"
    # 通过request获取具体检查结果，筛选出 checkitem,repdate,repdiag,repcontent
    # 合并输出 dataframe

    totalExamRes = []
    for exam in hExamList:
        if exam['fromdb'] == 'PECT':   # 这个非常坑
            exam['fromdb'] = 'PETCT'
        url = f"http://20.21.1.224:5537/api/api/LisReport/Get{exam['fromdb']}Detail/{mrn}/{exam['repo']}"
        examRes = requests.get(url).json()
        examRes = {key: examRes[key] for key in [
            'checkitem', 'repdate', 'repdiag', 'repcontent']}
        totalExamRes.append(examRes)

    if not totalExamRes:
        return "No match found"

    # print(totalExamRes)

    df = pd.DataFrame(totalExamRes)
    df = df.sort_values(by='repdate', ascending=False)
    df['repdate'] = pd.to_datetime(df['repdate'])
    df['repdate'] = df['repdate'].dt.strftime('%Y%m%d')

    df.rename(columns={'checkitem': '检查项目', 'repdate': '检查日期',
              'repdiag': '诊断', 'repcontent': '检查结果'}, inplace=True)

    # 定义一个函数，该函数会检查一个日期是否是今天的日期
    def highlight_today(row):
        if pd.to_datetime(row['检查日期']).date() == datetime.datetime.now().date():
            return ['background-color: yellow']*len(row)
        else:
            return ['']*len(row)

    # 使用 Styler 类的 set_table_styles 方法设置列宽
    examStyles = [
        {'selector': 'th.col_heading.level0.col0',
            'props': [('width', '100px')]},
        {'selector': 'th.col_heading.level0.col1',
            'props': [('width', '100px')]},
        {'selector': 'th.col_heading.level0.col2',
            'props': [('width', '100px')]},
        {'selector': 'th.col_heading.level0.col3',
            'props': [('width', '300px')]}
    ]

    return df.style.hide().apply(highlight_today, axis=1).set_table_styles(examStyles).to_html(classes="dataframe", table_id="testtable")


# hDocuList = requests.get(f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/4310592/11/emr").json()
def get_preAnesth(hDocuList):

    if isinstance(hDocuList, dict):
        return "No match found"

    # 筛选出hDocuList里docname为“麻醉前访视单”的字典
    hAnesthList = [item for item in hDocuList if item['docname'] == "麻醉前访视单"]

    # 如果hAnesthList为空，则返回空值
    if not hAnesthList:
        return "No match found"

    # 通过id和prlog_rdn获取病历文书内容
    mzurl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{hAnesthList[0]['id']}/{hAnesthList[0]['prlog_rdn']}/"

    # 获取网页内容
    response = requests.get(mzurl)

    # 从HTML中读取表格数据
    tables = pd.read_html(StringIO(response.text))

    # 每个表格都是一个DataFrame，你可以通过索引来访问它们
    # 我们需要第二个表格
    df = tables[2]

    # 筛选df第二列中包含“Yes”的行，获取第一列和最后2列
    df = df[df[2].str.contains("Yes", na=False)].iloc[:, [0, 3, 4]]

    return df.to_html(index=False, header=False)

# %%
# 护理记录
# http://20.21.1.224:5537/api/api/Physiorcd/GetNurDoc/5374115/8


def get_nurse_doc(mrn, series):
    nurseUrl = f"http://20.21.1.224:5537/api/api/Physiorcd/GetNurDoc/{mrn}/{series}"

    response = requests.get(nurseUrl)

    # 使用正则表达式匹配和提取字符串
    pattern = r"【过去史/近期手术/近期治疗】:(.*?)【个人史】"
    content = re.search(pattern, response.text, re.S)

    if content:
        content = content.group(1).strip()  # 提取匹配的内容，并去除前后的空白字符
    else:
        content = "No match found"

    return f"<!-- wp:paragraph -->\n<p class='nurse_doc'>\n{content}\n</p>\n<!-- /wp:paragraph -->"


# %%
# 医嘱
# http://20.21.1.224:5537/api/api/EmrCope/getPatientOrder/4878420/17/40/true


def get_order(mrn, series, idList, query):
    orderUrl = f"http://20.21.1.224:5537/api/api/EmrCope/getPatientOrder/{mrn}/{series}/40/true"

    response = requests.get(orderUrl).json()

    # 将response转换为dataframe，并筛选出 orderflag1, drname,dosage,frequency,ordertype,datestop
    # 保留datestop大于当前时间的行
    # 保留orderflag1 不为 NSC 的行
    df = pd.DataFrame(response)[
        ['orderflag1', 'drname', 'dosage', 'frequency', 'ordertype', 'datestop', 'duration']]
    # convert datestop column to timestamp object
    # 保留未停医嘱
    df['datestop'] = pd.to_datetime(df['datestop'])
    df = df[df['datestop'] > pd.Timestamp.now()]

    df = df[df['orderflag1'] != 'NSC']

    # 计算剩余时间
    df['dateleft'] = df['datestop'] - pd.Timestamp.now()

    # 抗生素列表
    antibioticList = ['[集采]头孢他啶针 1gX1', '哌拉西林']

    # workflow
    # 早上筛查出需要续期抗生素的列表，创建新卡片
    # 如果在中午前续期的话（续期时间大于48h）则会自动删除抗生素续期卡片，如果在下午续期的话就不会自动删除

    # 如果 df 的 drname 中包含在 antibioticList 中的元素的行，而且相应的 dateleft 大于 48 小时
    # 则检查trello里是否有“抗生素停用”card，有的话就删除
    if not df[df['drname'].isin(antibioticList) & (df['dateleft'] > pd.Timedelta(hours=48))].empty:
        response = requests.request(
            "GET",
            f"https://api.trello.com/1/lists/{idList}/cards",
            headers={"Accept": "application/json"},
            params=query).json()
        if any("抗生素即将停止使用，请注意！" in d['name'] for d in response):
            cardId = [d['id']
                      for d in response if "抗生素即将停止使用，请注意！" in d['name']]
            requests.request(
                "DELETE",
                f"https://api.trello.com/1/cards/{cardId[0]}",
                headers={"Accept": "application/json"},
                params=query
            )

    # 如果 df 的 drname 中包含在 antibioticList 中的元素的行，而且相应的 dateleft 小于 12 小时，则打印“抗生素即将停止使用，请注意！”
    if not df[df['drname'].isin(antibioticList) & (df['ordertype'] == "R") & (df['dateleft'] < pd.Timedelta(hours=12))].empty:
        # print("抗生素即将停止使用，请注意！")
        response = requests.request(
            "GET",
            f"https://api.trello.com/1/lists/{idList}/cards",
            headers={"Accept": "application/json"},
            params=query).json()
        # 如果 response 里的 name 列不含“抗生素即将停止使用，请注意！”，则创建新卡片
        if not any("抗生素即将停止使用，请注意！" in d['name'] for d in response):
            requests.request(
                "POST",
                "https://api.trello.com/1/cards",
                headers={"Accept": "application/json"},
                params=dict({"idList": idList,
                             "name": "抗生素即将停止使用，请注意！"},
                            **query)
            )

    ignoreList = ['饮水大于1500ML/日（如无禁忌）', '早期下床活动（如无禁忌）',
                  '宣教预防VTE相关知识', '氯化钠注射液 0.9%:100mlX1', '瑞芬太尼针 2mgX5', '[国产]舒芬太尼针 50ug:1mlX1']

    # 如果df的drname列包含ignoreList中的元素，则删除该行
    df = df[~df['drname'].isin(ignoreList)]

    # df 根据 ordertype 和 dateleft 逆序排序
    df = df.sort_values(by=['ordertype', 'dateleft'], ascending=[False, True])

    # dateleft列的显示格式改为  1days 5hours
    df['dateleft_dh'] = df['dateleft'].apply(
        lambda x: f"{x.days}d {x.seconds // 3600}h")

    df = df[['drname', 'ordertype', 'dosage',
             'frequency', 'dateleft', 'dateleft_dh']]
    df.rename(columns={'drname': '医嘱名称', 'ordertype': 'T',
              'dosage': '剂量', 'frequency': '频次', 'dateleft_dh': '剩余时间'}, inplace=True)

    # 使用 Styler 类的 set_table_styles 方法设置列宽

    orderStyles = [
        {'selector': 'th.col_heading.level0.col0',
            'props': [('width', '300px')]},
        {'selector': 'th.col_heading.level0.col1',
            'props': [('width', '50px')]},
        {'selector': 'th.col_heading.level0.col2',
            'props': [('width', '80px')]},
        {'selector': 'th.col_heading.level0.col3',
            'props': [('width', '80px')]},
        {'selector': 'th.col_heading.level0.col4',
            'props': [('width', '100px')]},
    ]

    # 定义一个函数，该函数会检查一个日期是否是今天的日期
    def highlight_today(row):
        if (row['dateleft'] < pd.Timedelta(hours=12)) & (row['T'] == "R"):
            return ['background-color: yellow']*len(row)
        else:
            return ['']*len(row)

    return df.style.hide(subset='dateleft', axis=1).hide().set_table_styles(orderStyles).apply(highlight_today, axis=1).to_html()


# %%
# 手术记录

# hDocuList = requests.get(f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/9454931/10/emr").json()
# hDocuList = requests.get(f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/9718076/2/emr").json()
def surgicalRecord(hDocuList):

    if isinstance(hDocuList, dict):
        return "No match found"

    # 筛选出hDocuList里docname为“麻醉前访视单”的字典
    hSurgicalRecord = [item for item in hDocuList if item['docname'] == "手术记录"]

    # 如果hAnesthList为空，则返回空值
    if not hSurgicalRecord:
        return "No match found"

    dfs = []
    for record in hSurgicalRecord:
        # 通过id和prlog_rdn获取病历文书内容
        srurl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{record['id']}/{record['prlog_rdn']}/"

        # 获取网页内容
        response = requests.get(srurl)

        # 从HTML中读取表格数据
        tables = pd.read_html(StringIO(response.text))

        # 每个表格都是一个DataFrame，你可以通过索引来访问它们
        data = {
            '手术日期': tables[2].iloc[0, 1],
            '手术名称': tables[3].iloc[5, 0],
            '术中所见': tables[3].iloc[7, 0],
            '手术经过': tables[3].iloc[9, 0]
        }

        df = pd.DataFrame(data, index=[0])
        dfs.append(df)

    result_df = pd.concat(dfs, ignore_index=True)

    # 使用 Styler 类的 set_table_styles 方法设置列宽
    surgicalStyles = [
        {'selector': 'th.col_heading.level0.col0',
            'props': [('width', '50px')]},
        {'selector': 'th.col_heading.level0.col1',
            'props': [('width', '150px')]},
        {'selector': 'th.col_heading.level0.col2',
            'props': [('width', '150px')]},
        {'selector': 'th.col_heading.level0.col3',
            'props': [('width', '250px')]}
    ]

    return result_df.style.set_table_styles(surgicalStyles).hide().to_html()

# %%
# 会诊


def consultation(hDocuList):

    if isinstance(hDocuList, dict):
        return "No match found"

    # 筛选出hDocuList里docname为“麻醉前访视单”的字典
    hconsultation = [item for item in hDocuList if item['docname'] == "会诊结果"]

    # # 如果hAnesthList为空，则返回空值
    if not hconsultation:
        return "No match found"

    dfs = []
    for consult in hconsultation:
        # 通过id和prlog_rdn获取病历文书内容
        consultationUrl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{consult['id']}/{consult['prlog_rdn']}/"

        # 获取网页内容
        response = requests.get(consultationUrl)

        # 从HTML中读取表格数据
        tables = pd.read_html(StringIO(response.text))

        # 每个表格都是一个DataFrame，你可以通过索引来访问它们
        data = {
            '会诊科室': tables[2].iloc[2, 2],
            '会诊医生': tables[2].iloc[2, 0].split("：")[1].strip(),
            '会诊时间': tables[4].iloc[0, 3],
            '会诊意见': ''.join(tables[3].iloc[2:, 0]).replace("注意事项：", "")
        }

        df = pd.DataFrame(data, index=[0])
        dfs.append(df)

    consultationRes = pd.concat(dfs, ignore_index=True)

    # 根据会诊时间逆序排列
    consultationRes = consultationRes.sort_values(by='会诊时间', ascending=False)

    def highlight_today(row):
        if (datetime.datetime.now().date() - pd.to_datetime(row['会诊时间']).date()).days <= 1:
            return ['background-color: yellow']*len(row)
        else:
            return ['']*len(row)

    # 使用 Styler 类的 set_table_styles 方法设置列宽
    consultationStyles = [
        {'selector': 'th.col_heading.level0.col0',
            'props': [('width', '50px')]},
        {'selector': 'th.col_heading.level0.col1',
            'props': [('width', '50px')]},
        {'selector': 'th.col_heading.level0.col2',
            'props': [('width', '100px')]},
        {'selector': 'th.col_heading.level0.col3',
            'props': [('width', '400px')]}
    ]

    return consultationRes.style.hide().set_table_styles(consultationStyles).apply(highlight_today, axis=1).to_html()

# %%
# 体温


def highcharts(mrn, series):

    tempUrl = f"http://20.21.1.224:5537/api/api/Physiorcd/GetPhysiorcdNsRef/{mrn}/{series}"

    response = requests.get(tempUrl).json()

    if not response:
        return "No match found"

    # 将response转换为dataframe
    # 筛选出content列包含“体温”的行
    # 筛选出pointInTimel和content列
    # 获取字符串“:36.8℃”中的“36.8”，并转换为数字格式保存至temp列
    df = pd.DataFrame(response)
    # 将 pointInTimel 列的时间转换为时间戳（以毫秒为单位）
    df['pointInTimel_utc'] = pd.to_datetime(
        df['pointInTimel']).dt.tz_localize('UTC').astype('int64') // 10**6

    # 创建 temp_df 的副本
    temp_df = df[df['content'].str.contains("体温", na=False)].copy()

    # 如果 temp_df 为空，则返回空值
    if temp_df.empty:
        return "No match found"

    # 使用正则表达式获取字符串中的数字部分, 并保存到temp列
    temp_df.loc[:, 'temp'] = temp_df['content'].str.extract(r'(\d+\.?\d+)')

    # 将temp列中的字符串转换为数字格式
    temp_df.loc[:, 'temp'] = pd.to_numeric(temp_df['temp'])

    # 删除temp列为na值的行
    temp_df = temp_df.dropna(subset=['temp'])

    temp_data = temp_df[['pointInTimel_utc', 'temp']].values.tolist()

    temp_data_str = ', '.join(str(pair) for pair in temp_data)

    # 血糖

    # 创建 temp_df 的副本
    glucose_df = df[df['content'].str.contains("血糖", na=False)].copy()

    # 如果 temp_df 为空，则返回空值
    if glucose_df.empty:
        return "No match found"

    # 使用正则表达式获取字符串中的数字部分, 并保存到glucose列
    glucose_df.loc[:, 'glucose'] = glucose_df['content'].str.extract(
        r'(\d+\.?\d+)')

    # 将glucose列中的字符串转换为数字格式
    glucose_df.loc[:, 'glucose'] = pd.to_numeric(glucose_df['glucose'])

    # 删除glucose列为na值的行
    glucose_df = glucose_df.dropna(subset=['glucose'])

    # 将 pointInTimel 和 temp 列配对保存到列表中
    glucose_data = glucose_df[['pointInTimel_utc', 'glucose']].values.tolist()

    glucose_data_str = ', '.join(str(pair) for pair in glucose_data)

    temp_glucose_chart = f"""
    <div id="container{mrn}" style="width: 600px;height:400px;"></div>
    <script>
    Highcharts.chart('container{mrn}', {{
        title: {{
            text: '体温血糖单'
        }},
        xAxis: {{
            type: 'datetime',
            labels: {{
                format: '{{value:%Y-%m-%d %H:%M}}'
            }}
        }},
        yAxis: [{{
            title: {{
                text: '体温'
            }},
            labels: {{
                enabled: false
            }},
            min: 30,
            max: 40,
            minorGridLineWidth: 0,
            gridLineWidth: 0,
            alternateGridColor: null,
            plotBands: {{ 
                from:  36,
                to: 38,
                color: 'rgba(68, 170, 213, 0.1)',
                label: {{
                    text: '体温',
                    style: {{
                        color: '#606060'
                    }}
                }}
            }}}}, 
            {{title: {{
                text: '血糖'
            }},
            labels: {{
                enabled: false
            }},
            min: 5,
            max: 18,
            minorGridLineWidth: 0,
            gridLineWidth: 0,
            alternateGridColor: null,
            opposite: true,
            plotBands: {{ 
                from: 7,
                to: 10,
                color: 'rgba(205, 92, 92, 0.1)',
                label: {{
                    text: '血糖',
                    style: {{
                        color: '#606060'
                    }}
                }}
            }}
        }}],
        colors: ['#ed551a', '#028dc7'],
        tooltip: {{
        headerFormat: '<b>{{series.name}}</b><br>',
        pointFormat: '{{point.x:%m-%d %H:%M%p }}: {{point.y:.2f}} mmol/L'
        }},
        series: [
            {{
            name: '体温',
            yAxis: 0,
            data: [{temp_data_str}]
        }},
            {{
            name: '血糖',
            yAxis: 1,
            data: [{glucose_data_str}]
        }}
        ]
    }});
    </script> \n
    """

    # 筛选df中content包含 “负压管”的行保存至draingage_df
    draingage_df = df[df['content'].str.contains('负压管', na=False)].copy()

    # 如果 draingage_df 为空，则返回空值
    if draingage_df.empty:
        return temp_glucose_chart

    print(draingage_df['content'])

    # 分割 draingage_df 的content列，以":"为标志，前面的保存至 tubeTag，后面部分去除“ml”字符后保存至volume列
    draingage_df[['tubeTag', 'volume']
                 ] = draingage_df['content'].str.split(':', expand=True)

    # 提取 volume 列中的数字
    draingage_df.loc[:, 'volume'] = draingage_df['volume'].str.replace(
        "ml", "").str.strip()

    # volume列转换为数值
    draingage_df.loc[:, 'volume'] = pd.to_numeric(draingage_df['volume'])

    # print(draingage_df[['pointInTimel','content','tubeTag','volume']])

    # 根据 tubeTag 列的值，构建列表，格式如下
    # [{name: tubeTag值1，data: [tubeTag值1对应的所有的pointInTimel_utc和volume值配对列表]}, {name: tubeTag值2，data: [tubeTag值2对应的所有的pointInTimel_utc和volume值配对列表]}]

    # 根据 tubeTag 列的值进行分组
    groups = draingage_df.groupby('tubeTag')

    # 对每个组，将 pointInTimel_utc 和 volume 列配对保存到列表中
    # 然后将每个组的名称和数据保存到字典中
    # 最后将所有的字典保存到列表中
    draingage_data = [{'name': name, 'data': group[[
        'pointInTimel_utc', 'volume']].values.tolist()} for name, group in groups]

    draingage_data_str = ', '.join(str(pair) for pair in draingage_data)

    # 替换draingage_data_str中的 'name':为 name：，'data': 为 data：
    draingage_data_str = re.sub(r"'name':", 'name:', draingage_data_str)
    draingage_data_str = re.sub(r"'data':", 'data:', draingage_data_str)

    draingage_chart = f"""
    <div id="draingage_container{mrn}" style="width: 600px;height:400px;"></div>
    <script>
    var chart = Highcharts.chart('draingage_container{mrn}', {{
        chart: {{
            type: 'spline'
        }},
        title: {{
            text: '引流量监测'
        }},
        xAxis: {{
            type: 'datetime',
            title: {{
                text: null
            }}
        }},
        colors: ['#6CF', '#39F', '#06C', '#036', '#000'],
        yAxis: {{
            title: {{
                text: 'ml'
            }},
            min: 0
        }},
        tooltip: {{
            headerFormat: '<b>{{series.name}}</b><br>',
            pointFormat: '{{point.x:%m-%d %H:%M%p }}: {{point.y:.2f}} ml'
        }},
        plotOptions: {{
            spline: {{
                marker: {{
                    enabled: true
                }}
            }}
        }},
        series: [{draingage_data_str}]
    }});
    </script> \n
    """

    return temp_glucose_chart + draingage_chart


# %%
# 手术安排

def surgical_arrange_check(pList):

    # 获取今天的日期
    today = datetime.date.today()

    # 获取今天是星期几（0=星期一，6=星期日）
    weekday = today.weekday()

    if weekday == 3:  # 周四
        fromDay = today  # 这周四
        toDay = today + rd.relativedelta(weekday=rd.FR)  # 周五
    elif weekday == 4:  # 周五
        fromDay = today + rd.relativedelta(weekday=rd.TH(-1))  # 周四
        toDay = today  # 这周五
    elif weekday == 5:  # 周六
        fromDay = today
        toDay = today + rd.relativedelta(weekday=rd.WE)
    else:
        fromDay = today + rd.relativedelta(weekday=rd.SA(-1))
        toDay = today + rd.relativedelta(weekday=rd.WE)

    if weekday == 2 or weekday == 3:
        nextFromDay = today + rd.relativedelta(weekday=rd.TH)
        nextToDay = today + rd.relativedelta(weekday=rd.FR)
    elif weekday == 0 or weekday == 1 or weekday == 6:
        nextFromDay = today + rd.relativedelta(weekday=rd.SA(-1))
        nextToDay = today + rd.relativedelta(weekday=rd.WE)
    elif weekday == 4 or weekday == 5:
        nextFromDay = today + rd.relativedelta(weekday=rd.SA)
        nextToDay = today + rd.relativedelta(weekday=rd.WE)

    # 将日期格式化为字符串
    fromDay_str = fromDay.strftime('%Y-%m-%d')
    toDay_str = toDay.strftime('%Y-%m-%d')
    nextFromDay_str = nextFromDay.strftime('%Y-%m-%d')
    nextToDay_str = nextToDay.strftime('%Y-%m-%d')

    # arrange surgery
    arrange_unRegister = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{nextFromDay_str}/{nextToDay_str}/1/33A/30046/"
    ).json()
    arrange_notYetAdmintted = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{nextFromDay_str}/{nextToDay_str}/5/33A/30046/"
    ).json()
    arrange_alreadyAdmintted = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{nextFromDay_str}/{nextToDay_str}/7/33A/30046/"
    ).json()

    # 合并 unRegister, notYetAdmintted, alreadyAdmintted，并转换为dataframe
    arrangeListdf = pd.DataFrame(
        arrange_unRegister+arrange_alreadyAdmintted+arrange_notYetAdmintted)
    arrangeListdf = arrangeListdf[['PatientName',  'PatientID',  'Isroom', 'Diagnose', 'drremark', 'PatientSex', 'PatientAge',
                                   'Doctor', 'NoticeFlag', 'AppointmentIn', 'AppOperativeDate']]
    # 删除bookList的 NoticeFlag为“取消”的行
    arrangeListdf = arrangeListdf[arrangeListdf['NoticeFlag'] != '取消']

    arrangeListdf.to_excel(f"D:\working-sync\手术通知\{nextToDay_str}.xlsx", index=False)

    # check surgery
    unRegister = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{fromDay_str}/{toDay_str}/1/33A/30046/"
    ).json()
    notYetAdmintted = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{fromDay_str}/{toDay_str}/5/33A/30046/"
    ).json()
    alreadyAdmintted = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{fromDay_str}/{toDay_str}/7/33A/30046/"
    ).json()

    # 合并 unRegister, notYetAdmintted, alreadyAdmintted，并转换为dataframe
    bookListdf = pd.DataFrame(unRegister+notYetAdmintted+alreadyAdmintted)

    bookList = bookListdf[['PatientName', 'drremark', 'PatientID', 'NoticeFlag', 'PatientSex',
                           'AppointmentIn', 'AppOperativeDate', 'Doctor', 'Diagnose', 'Isroom', 'PatientAge']].copy()
    # bookList 的PatientID列名改为mrn
    bookList.rename(columns={'PatientID': 'mrn'}, inplace=True)
    # 删除bookList的 NoticeFlag为“取消”的行
    bookList = bookList[bookList['NoticeFlag'] != '取消']
    # 将 'mrn' 列转换为字符串类型
    bookList.loc[:, 'mrn'] = bookList['mrn'].astype(str)
    pList.loc[:, 'mrn'] = pList['mrn'].astype(str)

    # 删除pList里mrn列与booklist中的mrn列相同的行
    pListLeft = pList[~pList['mrn'].isin(bookList['mrn'])]

    surgicalListRaw = requests.get(
        f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77A/5/A002/{toDay_str}"
    ).json()

    surgicalList = pd.DataFrame(surgicalListRaw)

    if not surgicalList.empty:
        surgicalList = surgicalList[[
            'mrn', 'pname', 'room', 'cdo', 'operp', 'name']]
        surgicalList = surgicalList[surgicalList['name'] == '李文雅']
        surgicalList.loc[:, 'mrn'] = surgicalList['mrn'].astype(str)

        #  根据bookList 和 surgicalList的 mrn 列合并，要求保留booklist的所有行
        surgicalCheck = pd.merge(bookList, surgicalList, on='mrn', how='left')

        surgicalCheck = surgicalCheck[['room', 'cdo', 'PatientName', 'mrn', 'PatientSex', 'PatientAge',
                                       'Isroom', 'Diagnose', 'drremark', 'operp', 'Doctor']]
        # surgicalCheck 根据 room 和 cdo 升序排序
        surgicalCheck = surgicalCheck.sort_values(by=['room', 'cdo'])
        # 并将cdo列改成int格式
        surgicalCheck.loc[:, 'cdo'] = surgicalCheck['cdo'].astype(
            str).replace('.0', '', regex=True)

        inpatientCheck = pd.merge(pListLeft, surgicalList, on=['mrn', 'pname'], how='left')[
            ['room', 'cdo', 'bedid', 'pname', 'mrn', 'diag', 'operp']]

    else:
        surgicalCheck = bookList[['PatientName', 'mrn', 'PatientSex',
                                  'PatientAge', 'Isroom', 'Diagnose', 'drremark', 'Doctor']]
        inpatientCheck = pListLeft[['bedid', 'pname', 'mrn', 'diag']]

    return surgicalCheck, inpatientCheck, arrangeListdf
