import re
import requests
import pandas as pd
from io import StringIO
import dateutil.relativedelta as rd
import datetime


"""
wordpress css snippet

table {
    width: 600px;
    table-layout: fixed;
}

table td {
    word-wrap: break-word;
}

.table-container table {
	width: 1500px;
	table-layout: auto;
}

.table-container {
    width: 600px;
    overflow-x: auto;
}

.nurse_doc {
	width: 600px;
}

.note_link {
	color: black;
}

h2 {
    position: sticky;
    top: 0;
    background-color: white;
    z-index: 100000;
	width: 600px;
	white-space: nowrap;
    overflow-x: auto;

}

h4 {
	width: 600px;
}

form {
	width: 600px;
}
"""

"""
trello 递交表单

<script>
// JavaScript
$(document).ready(function(){
  $('.myForm').on('submit', function(e){
    e.preventDefault();
    var form = $(this); // 保存对表单的引用
    var list_id = form.find('.list_id').val();
    var name = form.find('.name').val();
    var messageElement = form.next('.message');
    $.ajax({
      url: 'https://api.trello.com/1/cards',
      type: 'POST',
      data: {
        key: 'f45b896485c79fe922e7f022a8bc6f71',
        token: 'ATTAae59e22e7d144839c54a444aa4f24d4f3ede09405b11ace472e773a78a23b0e8F2D629A2',
        idList: list_id,
        name: name
      },
      success: function(response){
        console.log(response);
        form.find('.name').val(''); // 清空文本框
        messageElement.text('递交成功'); // 显示递交成功的消息
        setTimeout(function() {
          messageElement.text(''); // 1 秒后清除消息
        }, 1000);
      },
      error: function(error){
        console.log(error);
        messageElement.text('递交失败'); // 显示递交失败的消息
      }
    });
  });
});
</script>

"""


# %%
# 根据住院号获得检查列表
def get_lab_results(mrn, duration):
    hLabList = requests.get(
        f"http://20.21.1.224:5537/api/api//LisReport/GetLisReportIndexHalf/{mrn}/1").json()

    # 创建一个字典，用于替换checkitem里的内容
    checkitemDict = {
        "CBC,ABO输血,RH输血": "血常规",
        "HCVAb,HIVAb,梅毒筛选,AHBCIgM,前S抗原,乙肝定量": "术前免疫",
        "HBsAg快,HCVAb快,HIVAgAb,梅毒快,TRUST,梅毒TPPA": "日间免疫",
        "ABScreen,Rh表型CcEe": "血型"}

    # %%
    # 利用字典替换hLabList里checkitem的内容
    for item in hLabList:
        item['checkitem'] = checkitemDict.get(
            item['checkitem'], item['checkitem'])

    # 如果 hLabList 中 checkitem 包含 "生化"或者“ADA”或者“肝功能”，则将 checkitem 替换为 "生化全套"
    for item in hLabList:
        if "生化" in item['checkitem'] or "ADA" in item['checkitem'] or "肝功能" in item['checkitem'] or "电解质" in item['checkitem']:
            item['checkitem'] = "生化检查"

    for item in hLabList:
        if "血气" in item['checkitem']:
            item['checkitem'] = "血气检查"

    # 根据hLabList里的bgsj筛选出大于当前日期-duration（天）的数据
    hLabListLimit = [item for item in hLabList if (
        pd.Timestamp.now() - pd.Timestamp(item['repdate'])).days <= duration]

    checkitemList = ['CBC', 'hsCRP', "生化检查", "血气检查"]
    # 筛选出 hLabList 中 checkitem 包含在 checkitemList 中的字典
    hLabListSelect = [item for item in hLabList if item['checkitem'] in checkitemList and (
        pd.Timestamp.now() - pd.Timestamp(item['repdate'])).days > duration]

    # hLabListSelect按照checkitem分组，选取每一组中时间最近的一条数据
    if hLabListSelect:
        hLabListSelect = pd.DataFrame(hLabListSelect).sort_values(
            by=['checkitem', 'repdate'], ascending=[True, False]).groupby('checkitem').head(1).to_dict(orient='records')

    # 合并hLabListLimit和hLabListSelect
    hLabListTotal = hLabListLimit+hLabListSelect

    if not hLabListTotal:
        return "No match found"

    totalLabRes = []
    for lab in hLabListTotal:
        url = f"http://20.21.1.224:5537/api/api/LisReport/GetLisReportDetail/{
            mrn}/{lab['dodate']}/{lab['specimenid']}/{lab['domany']}"
        labRes = requests.get(url).json()
        for item in labRes:
            # item['bgsj'] = lab['repdate']
            item['checkitem'] = lab['checkitem']
        totalLabRes.extend(labRes)  # 将 labRes 的结果添加到 totalLabRes 列表中

    df = pd.DataFrame(totalLabRes)  # 将 totalLabRes 列表转换为 DataFrame
    df = df[['xmmc', 'jg', 'zdbz', 'ckqj', 'bgsj', 'checkitem']]  # 选择需要的列

    # 创建一个包含重点检验结果名称的列表
    important_tests = ["血小板计数", "白细胞计数", "中性粒百分数", "血红蛋白量", "钾", "钙", "肌酐",
                       "葡萄糖", '尿素/肌酐', '丙氨酸氨基转移酶', '天冬氨酸氨基转移酶', '白蛋白', '超敏C反应蛋白', 'D-二聚体(D-Di)']

    # 删除df中 bgsj 小于当前日期-duration天 且 xmmc 不在 important_tests 中的行
    df = df[~(((pd.Timestamp.now() - pd.to_datetime(df['bgsj'], format="mixed")
                ).dt.days > duration) & (~df['xmmc'].isin(important_tests)))]

    def process_group(group):
        if group['zdbz'].replace('', pd.NA).isnull().all():  # 如果 'zdbz' 列都是空白
            return pd.DataFrame([{
                'xmmc': '',
                'jg': 'all阴性',
                'zdbz': '',
                'ckqj': '',
                'bgsj': group['bgsj'].iloc[0],
                'checkitem': group['checkitem'].iloc[0]
            }])
        else:
            # 删除 'zdbz' 为空白的行
            return group[group['zdbz'].replace('', pd.NA).notnull()]

    df = df.groupby('checkitem').apply(process_group).reset_index(drop=True)

    # 将df按照bgsj由大到小逆向排序
    df = df.sort_values(by='bgsj', ascending=False)
    # 将bgsj转换成日期格式
    df['bgsj'] = pd.to_datetime(df['bgsj']).dt.strftime('%Y-%m-%d')

    df.rename(columns={'xmmc': '项目名称', 'jg': '结果', 'zdbz': 'R',
              'ckqj': '参考范围', 'bgsj': '检验日期', 'checkitem': '检验项目'}, inplace=True)

    # 定义一个函数，该函数会检查一个日期是否是今天的日期
    def highlight_today(row):
        if pd.to_datetime(row['检验日期']).date() == datetime.datetime.now().date():
            return ['background-color: yellow']*len(row)
        else:
            return ['']*len(row)

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
        url = f"http://20.21.1.224:5537/api/api/LisReport/Get{
            exam['fromdb']}Detail/{mrn}/{exam['repo']}"
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

    return df.style.apply(highlight_today, axis=1).hide().set_table_styles(examStyles).to_html(classes="dataframe", table_id="testtable")


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
    mzurl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{
        hAnesthList[0]['id']}/{hAnesthList[0]['prlog_rdn']}/"

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
    nurseUrl = f"http://20.21.1.224:5537/api/api/Physiorcd/GetNurDoc/{
        mrn}/{series}"

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
    orderUrl = f"http://20.21.1.224:5537/api/api/EmrCope/getPatientOrder/{
        mrn}/{series}/40/true"

    response = requests.get(orderUrl).json()

    if not response:
        return "No match found"

    # 将response转换为dataframe，并筛选出 orderflag1, drname,dosage,frequency,ordertype,datestop
    # 保留datestop大于当前时间的行
    # 保留orderflag1 不为 NSC 的行
    df = pd.DataFrame(response)[
        ['orderflag1', 'drname', 'dosage', 'frequency', 'ordertype', 'datestop', 'datestart', 'mark']]
    df = df[df['mark'] != '护理评估智能决策']
    df = df[df['orderflag1'] != 'NSC']
    # convert datestop column to timestamp object
    # 保留未停医嘱
    df['datestop'] = pd.to_datetime(df['datestop'])
    df['datestart'] = pd.to_datetime(df['datestart'])

    # df筛选出ordertype为"R"且datestop列大于当前时间的行 或者 ordertype为"S"且datestart列大于当前日期提前一天的行
    df = df[((df['datestop'] > pd.Timestamp.now()) & (df['ordertype'] == "R")) |
            ((df['datestart'] > pd.Timestamp.now().normalize() - pd.Timedelta(days=1)) & (df['ordertype'] == "S"))]

    # 创建一个字典，用于替换checkitem里的内容
    # 比如将 “ADA,CA,AST,ALP,GGT,MG,PHOS,CK,LDH,hsCRP,同型半胱氨,CysC,D3-H,NEFA,RBP,SAA,TBA,LP(a),*LDL,‖生化筛查”替换为“生化全套”
    orderItemDict = {
        "GGT/MG/同型半胱氨酸/生化筛查常规检查/视黄醇结合蛋白/TBA(空腹)/血清胱抑素(Cystatin C)测定/β-羟丁酸/游离脂肪酸/Ca/AST/血清淀粉样蛋白/超敏C反应蛋白(hsCRP)/LP(a)/LDL/ADA:血清/ALP/PHO": "生化全套",
        "纤维蛋白原(FG)/部分凝血活酶时间(APTT)/凝血酶原时间(PT)/D-Di(仅限入院筛查)": "凝血功能全套",
        "梅毒筛选/AHBCIgM/前S抗原/乙肝三系检查/HIVAb/HCVAb": "术前免疫",
        "HBsAg快,HCVAb快,HIVAgAb,梅毒快,TRUST,梅毒TPPA": "日间免疫",
        "ABScreen,Rh表型CcEe": "血型"}
    # 利用字典替换checkitem列的内容
    df['drname'] = df['drname'].replace(orderItemDict)

    # 计算剩余时间
    df['dateleft'] = df['datestop'] - pd.Timestamp.now()

    # 抗生素列表
    antibioticList = [
        '[集采]头孢他啶针 1gX1',
        '[集采]左氧氟沙星针 0.5g:100mlX1',
        '[集采]哌拉西林他唑巴坦针 4.5g(4.0g/0.5g)X1',
        '亚胺培南西司他丁针 0.5/0.5gX1',
        '[西力欣]头孢呋辛针 750mgX1',
        '[合资]哌拉西林他唑巴坦针 4.5g(4.0g/0.5g)X1',
        '头孢哌酮舒巴坦针 1.5gX1',
        '亚胺培南西司他丁针 0.5/0.5gX1',
        '[北京]左氧氟沙星针 0.5g:100mlX1',
    ]

    # workflow
    # 早上筛查出需要续期抗生素的列表，创建新卡片
    # 一个负责加一个负责删除

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

    # 如果 df 的 drname 中包含在 antibioticList 中的元素的行，而且相应的 dateleft 大于 48 小时
    # 则检查trello里是否有“抗生素停用”card，有的话就删除
    if not df[df['drname'].isin(antibioticList) & (df['dateleft'] > pd.Timedelta(hours=24))].empty:
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

    ignoreList = ['饮水大于1500ML/日（如无禁忌）', '早期下床活动（如无禁忌）',
                  '宣教预防VTE相关知识',
                  '氯化钠注射液 0.9%:100mlX1',
                  '瑞芬太尼针 2mgX5',
                  '[集采]右美托咪定针 200ug:2mlX1',
                  '[进口]罗哌卡因针 75mg:10mlX5',
                  '间羟胺针 10mg:1mlX2',
                  '麻黄硷针 30mg:1mlX10',
                  '[仙居]苯磺顺阿曲库铵针 5mgX1',
                  '[凯特力]七氟烷 ml',
                  '乳酸钠林格注射液 500mlX1',
                  '[万汶]羟乙基淀粉针 500ml:30g/4.5gX1',
                  '复方电解质针 500mlX1',
                  '瑞马唑仑针 36mgX1',
                  '依托咪酯针 20mg:10mlX1',
                  '格拉司琼针 3mg:3mlX5',
                  '阿托品针 0.5mg:1mlX10',
                  '纳布啡针 1ml:10mgX1',
                  '[竟安]丙泊酚中/长链脂肪乳针 0.5g:50mlX1',
                  '新斯的明针 1mg:2mlX10',
                  '[国产]舒芬太尼针 50ug:1mlX1',
                  '[集采]丙泊酚中/长链脂肪乳针 0.2g:20mlX1',
                  '',
                  '',
                  '',
                  '',
                  '',
                  ]

    # 如果df的drname列包含ignoreList中的元素，则删除该行
    df = df[~df['drname'].isin(ignoreList)]

    # df 根据 ordertype 和 dateleft 逆序排序
    df = df.sort_values(by=['ordertype', 'dateleft'], ascending=[True, True])

    # dateleft列的显示格式改为  1days 5hours
    df['dateleft_dh'] = df['dateleft'].apply(
        lambda x: f"{x.days}d {x.seconds // 3600}h")

    df = df[['drname', 'ordertype', 'dosage',
             'frequency', 'dateleft', 'dateleft_dh', 'datestart', 'datestop']]
    df.rename(columns={'drname': '医嘱名称', 'ordertype': 'T',
              'dosage': '剂量', 'frequency': '频次', 'dateleft_dh': '剩余时间'}, inplace=True)

    # 使用 Styler 类的 set_table_styles 方法设置列宽

    orderStyles = [
        {'selector': 'th.col_heading.level0.col0',
            'props': [('width', '300px')]},         # 医嘱名称
        {'selector': 'th.col_heading.level0.col1',
            'props': [('width', '50px')]},          # T
        {'selector': 'th.col_heading.level0.col2',
            'props': [('width', '90px')]},          # 剂量
        {'selector': 'th.col_heading.level0.col3',
            'props': [('width', '80px')]},          # 频次
        {'selector': 'th.col_heading.level0.col4',
            'props': [('width', '100px')]},         # 剩余时间
        {'selector': 'th.col_heading.level0.col5',
            'props': [('width', '300px')]},         # datestart
        {'selector': 'th.col_heading.level0.col6',
            'props': [('width', '300px')]},         # datestop
    ]

    # 定义固定列的样式
    columnFixStyle = [
        {'selector': 'tr:nth-child(odd) th:nth-child(1), tr:nth-child(odd) td:nth-child(1)',
         'props': 'position: -webkit-sticky; position: sticky; left:0px; background-color: #f6f6f6;'},
        {'selector': 'tr:nth-child(even) th:nth-child(1), tr:nth-child(even) td:nth-child(1)',
         'props': 'position: -webkit-sticky; position: sticky; left:0px; background-color: #ffffff;'},
        {'selector': 'tr:nth-child(odd) th:nth-child(2), tr:nth-child(odd) td:nth-child(2)',
         'props': 'position: -webkit-sticky; position: sticky; left:300px; background-color: #f6f6f6;'},
        {'selector': 'tr:nth-child(even) th:nth-child(2), tr:nth-child(even) td:nth-child(2)',
         'props': 'position: -webkit-sticky; position: sticky; left:300px; background-color: #ffffff;'},
    ]

    # 定义一个函数，该函数会检查一个日期是否是今天的日期

    def highlight_today(row):
        if (row['dateleft'] < pd.Timedelta(hours=12)) & (row['T'] == "R"):
            return ['background-color: yellow']*len(row)
        else:
            return ['']*len(row)

    return df.style.hide(subset='dateleft', axis=1).hide().set_table_attributes('style="width:1300px;"').set_table_styles(orderStyles+columnFixStyle).apply(highlight_today, axis=1).to_html()

    # return df.style.hide(subset='dateleft', axis=1).hide().set_table_styles(orderStyles).apply(highlight_today, axis=1).to_html()
    # return df.style.hide(subset='dateleft', axis=1).hide().apply(highlight_today, axis=1).to_html()
    # return df.to_html()

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
        srurl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{
            record['id']}/{record['prlog_rdn']}/"

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
    hconsultationApply = [
        item for item in hDocuList if item['docname'] == "会诊申请"]

    hconsultationReply = [
        item for item in hDocuList if item['docname'] == "会诊结果"]

    # 如果 hconsultationApply 和 hconsultationReply 都为空，则返回空值
    if not hconsultationApply and not hconsultationReply:
        return "No match found"

    dfs = []

    if hconsultationApply:
        for consult in hconsultationApply:
            # 通过id和prlog_rdn获取病历文书内容
            consultationUrl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{
                consult['id']}/{consult['prlog_rdn']}/"

            # 获取网页内容
            response = requests.get(consultationUrl)

            # 从HTML中读取表格数据
            tables = pd.read_html(StringIO(response.text))

            # 每个表格都是一个DataFrame，你可以通过索引来访问它们
            data = {
                '会诊科室': "A" + tables[2].iloc[2, 1],
                '会诊医生': tables[2].iloc[1, 1],
                '会诊时间': tables[2].iloc[1, 3],
                '会诊意见': ''.join(tables[3].iloc[:, 0])
            }

            df = pd.DataFrame(data, index=[0])
            dfs.append(df)

    if hconsultationReply:
        for consult in hconsultationReply:
            # 通过id和prlog_rdn获取病历文书内容
            consultationUrl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{
                consult['id']}/{consult['prlog_rdn']}/"

            # 获取网页内容
            response = requests.get(consultationUrl)

            # 从HTML中读取表格数据
            tables = pd.read_html(StringIO(response.text))

            # 每个表格都是一个DataFrame，你可以通过索引来访问它们
            data = {
                '会诊科室': "R" + tables[2].iloc[2, 2],
                '会诊医生': tables[2].iloc[2, 0].split("：")[1].strip(),
                '会诊时间': tables[4].iloc[0, 3],
                '会诊意见': ''.join(tables[3].iloc[2:, 0]).replace("注意事项：", "")
            }

            df = pd.DataFrame(data, index=[0])
            dfs.append(df)

    consultationRes = pd.concat(dfs, ignore_index=True)

    # 根据会诊时间逆序排列
    consultationRes = consultationRes.sort_values(by='会诊时间', ascending=False)

    # 删除会诊时间距离当前日期大于1周的行
    consultationRes = consultationRes[(
        datetime.datetime.now() - pd.to_datetime(consultationRes['会诊时间'])).dt.days <= 7]

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


def medicalHistory(hDocuList):

    if isinstance(hDocuList, dict):
        return "No match found"

    historyList = [
        item for item in hDocuList if item['docname'] == "首次病程录（新版）"]

    if not historyList:
        return "No match found"

    historyUrl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{
        historyList[0]['id']}/{historyList[0]['prlog_rdn']}/"

    # 获取网页内容
    response = requests.get(historyUrl)

    # 从HTML中读取表格数据
    tables = pd.read_html(StringIO(response.text))

    medicalHistory = tables[3].iloc[1, 0]

    # 使用正则表达式分割字符串
    parts = re.split(r'(\d+、)', medicalHistory)

    # 在每个部分之间添加回车键
    parts = [parts[i] + '<br>' if i % 2 == 0 else parts[i]
             for i in range(len(parts))]

    # 使用空字符串合并所有部分
    medicalHistoryRes = ''.join(parts)

    return f"<!-- wp:paragraph -->\n<p class='nurse_doc'>\n{medicalHistoryRes}\n</p>\n<!-- /wp:paragraph -->"


# %%
# 体温
"""
wordpress 用 添加 html snippet

<script src="https://code.hcharts.cn/highcharts.js"></script>
"""


def highcharts(mrn, series):

    tempUrl = f"http://20.21.1.224:5537/api/api/Physiorcd/GetPhysiorcdNsRef/{
        mrn}/{series}"

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

    # draingage_df = df[df['content'].str.contains('负压管|皮下引流管', na=False)].copy()
    # 创建一个列表
    tube_types = ["负压管", "皮下引流管", "腹腔负压引流", "管", "引流"]

    # 使用 join() 函数将列表中的元素连接成一个字符串
    tube_types_str = "|".join(tube_types)

    # 使用这个字符串和正则表达式进行筛选
    draingage_df = df[df['content'].str.extract(
        f'({tube_types_str})\\d*: *\\d+ml', expand=False).notna()].copy()

    # 如果 draingage_df 为空，则返回空值
    if draingage_df.empty:
        return temp_glucose_chart

    # print(draingage_df['content'])

    # 分割 draingage_df 的content列，以":"为标志，前面的保存至 tubeTag，后面部分去除“ml”字符后保存至volume列
    draingage_df[['tubeTag', 'volume']
                 ] = draingage_df['content'].str.split(':', expand=True)

    # 提取 volume 列中的数字
    draingage_df.loc[:, 'volume'] = draingage_df['volume'].str.replace(
        "ml", "").str.strip()

    # volume列转换为数值
    draingage_df.loc[:, 'volume'] = pd.to_numeric(draingage_df['volume'])

    # 如果content里包含“尿”，则将volume列的值除以10，并在content的内容里添加“/10”
    draingage_df.loc[draingage_df['tubeTag'].str.contains(
        "尿", na=False), 'volume'] = draingage_df['volume'] / 10
    draingage_df.loc[draingage_df['tubeTag'].str.contains(
        "尿", na=False), 'tubeTag'] = draingage_df['tubeTag'] + "/10"

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


"""
wordpress 用 wpcode 新建 PHP snippet

function my_ajax_handler() {
    // 获取请求参数
    $list_id = $_POST['list_id'];

    // 设置Trello API的URL和请求头
    $url = "https://api.trello.com/1/lists/{$list_id}/cards";
    $args = array(
        'headers' => array(
            'Accept' => 'application/json'
        ),
        'body' => array(
            'key' => 'f45b896485c79fe922e7f022a8bc6f71',
            'token' => 'ATTAae59e22e7d144839c54a444aa4f24d4f3ede09405b11ace472e773a78a23b0e8F2D629A2'
        )
    );

    // 发起GET请求
    $response = wp_remote_get($url, $args);

    // 检查是否有错误
    if (is_wp_error($response)) {
        wp_send_json_error();
    } else {
        wp_send_json_success(wp_remote_retrieve_body($response));
    }
}
add_action('wp_ajax_my_ajax_handler', 'my_ajax_handler');
add_action('wp_ajax_nopriv_my_ajax_handler', 'my_ajax_handler');
"""


def trello_note(trelloListId, place):
    trello_note_ajax = f"""
    <script>
    jQuery(document).ready(function ($) {{
        $.ajax({{
            url: '/wp-admin/admin-ajax.php',
            type: 'POST',
            data: {{
                action: 'my_ajax_handler',
                list_id: '{trelloListId}'
            }},
            success: function (response) {{
                if (response.success) {{
                    var cards = JSON.parse(response.data);
                    cards.forEach(function (card) {{
                        var name = card.name; // 获取每个card对象的name属性值
                        var shortUrl = card.shortUrl;
                        $('#trello-content-{place}-{trelloListId}').append("<li><a href='"+ shortUrl+"' target='_blank'>"+name+ "</a></li><br>"); // 将每个card的name属性显示在页面上
                    }});
                }} else {{
                    $('#trello-content-1').append("Ajax请求失败")
                    console.error('Ajax请求失败');
                }}
            }}
        }});
    }});
    </script>

    <div id="trello-content-{place}-{trelloListId}">
    <!-- Trello的内容将在这里显示 -->
    </div>
    """

    return trello_note_ajax


# %%
# 手术安排

def surgical_arrange(pList, attending, aName):

    today = datetime.date.today() + datetime.timedelta(days=0)

    # 获取今天是星期几（0=星期一，6=星期日）
    weekday = today.weekday()

    if weekday == 2:
        lastSurgeryDate = today + rd.relativedelta(weekday=rd.TU(-1))
        prelastSurgeryDate = today + rd.relativedelta(weekday=rd.TH(-1))
        upcomingSurgeryDate = today + rd.relativedelta(weekday=rd.TH)
        nextSurgeyDate = today + rd.relativedelta(weekday=rd.TU)
    elif weekday == 3:
        lastSurgeryDate = today + rd.relativedelta(weekday=rd.TU(-1))
        prelastSurgeryDate = today + rd.relativedelta(weekday=rd.TH(-2))
        upcomingSurgeryDate = today + rd.relativedelta(weekday=rd.TH)
        nextSurgeyDate = today + rd.relativedelta(weekday=rd.TU)
    elif weekday == 1:
        lastSurgeryDate = today + rd.relativedelta(weekday=rd.TH(-1))
        prelastSurgeryDate = today + rd.relativedelta(weekday=rd.TU(-2))
        upcomingSurgeryDate = today + rd.relativedelta(weekday=rd.TU)
        nextSurgeyDate = today + rd.relativedelta(weekday=rd.TH)
    else:
        lastSurgeryDate = today + rd.relativedelta(weekday=rd.TH(-1))
        prelastSurgeryDate = today + rd.relativedelta(weekday=rd.TU(-1))
        upcomingSurgeryDate = today + rd.relativedelta(weekday=rd.TU)
        nextSurgeyDate = today + rd.relativedelta(weekday=rd.TH)

    # print(today, today.weekday()+1)
    # print(prelastSurgeryDate, prelastSurgeryDate.weekday()+1)
    # print(lastSurgeryDate, lastSurgeryDate.weekday()+1)
    # print(upcomingSurgeryDate, upcomingSurgeryDate.weekday()+1)
    # print(nextSurgeyDate, nextSurgeyDate.weekday()+1)

    # %%
    # 将日期格式化为字符串
    # today_str = today.strftime('%Y-%m-%d')
    lastSurgeryDate_str = lastSurgeryDate.strftime('%Y-%m-%d')
    prelastSurgeryDate_str = prelastSurgeryDate.strftime('%Y-%m-%d')
    upcomingSurgeryDate_str = upcomingSurgeryDate.strftime('%Y-%m-%d')
    nextSurgeyDate_str = nextSurgeyDate.strftime('%Y-%m-%d')

    # arrange surgery
    schedule_unRegister = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{
            prelastSurgeryDate_str}/{nextSurgeyDate_str}/1/33/{attending}/"
    ).json()
    schedule_notYetAdmintted = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{
            prelastSurgeryDate_str}/{nextSurgeyDate_str}/5/33/{attending}/"
    ).json()
    schedule_alreadyAdmintted = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{
            prelastSurgeryDate_str}/{nextSurgeyDate_str}/7/33/{attending}/"
    ).json()

    # 合并 unRegister, notYetAdmintted, alreadyAdmintted，并转换为dataframe
    surgeryScheduleDF = pd.DataFrame(
        schedule_unRegister+schedule_notYetAdmintted+schedule_alreadyAdmintted)

    # %%
    surgeryScheduleDF = surgeryScheduleDF[['PatientName',  'PatientID',  'Isroom', 'Diagnose', 'drremark', 'PatientSex', 'PatientAge',
                                           'Doctor', 'NoticeFlag', 'AppointmentIn', 'AppOperativeDate', 'arrangedate', 'dohoscode']]
    # 删除bookList的 NoticeFlag为“取消”的行
    surgeryScheduleDF = surgeryScheduleDF[surgeryScheduleDF['NoticeFlag'] != '取消']

    # arrangeListdf.to_excel(
    #     f"D:\\working-sync\\手术通知\\预约清单-{nextToDay_str}-{aName}.xlsx", index=False)

    surgeryScheduleDF.rename(
        columns={'PatientID': 'mrn', 'PatientName': 'pname', 'Diagnose': 'diag'}, inplace=True)

    surgeryScheduleDF.loc[:, 'mrn'] = surgeryScheduleDF['mrn'].astype(str)
    pList.loc[:, 'mrn'] = pList['mrn'].astype(str)

    # 将surgeryScheduleDF和pList根据mrn列合并
    scheduleList = surgeryScheduleDF.merge(
        pList[['mrn', 'bedid']], on=['mrn'], how="left")

    # 删除 schdeuleList 里 dohoscode为 钱塘院区 的行
    scheduleList = scheduleList[scheduleList['dohoscode'] != '钱塘院区']

    scheduleList.loc[:, 'AppointmentIn'] = scheduleList['AppointmentIn'].str.replace(
        "T00:00:00", "")
    scheduleList.loc[:, 'AppOperativeDate'] = scheduleList['AppOperativeDate'].str.replace(
        "T00:00:00", "")
    scheduleList.loc[:, 'arrangedate'] = scheduleList['arrangedate'].str.replace(
        "T00:00:00", "")

    # %%

    prelastSurgeryList = pd.DataFrame(requests.get(
        f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/5/A001/{
            prelastSurgeryDate_str}"
    ).json())

    prelastSurgeryList = prelastSurgeryList[[
        'mrn', 'pname', 'room', 'cdo', 'operp', 'name', 'plandate']]
    prelastSurgeryList = prelastSurgeryList[prelastSurgeryList['name'] == aName]
    prelastSurgeryList.loc[:, 'mrn'] = prelastSurgeryList['mrn'].astype(str)

    lastSurgeryList = pd.DataFrame(requests.get(
        f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/5/A001/{
            lastSurgeryDate_str}"
    ).json())

    lastSurgeryList = lastSurgeryList[[
        'mrn', 'pname', 'room', 'cdo', 'operp', 'name', 'plandate']]
    lastSurgeryList = lastSurgeryList[lastSurgeryList['name'] == aName]
    lastSurgeryList.loc[:, 'mrn'] = lastSurgeryList['mrn'].astype(str)

    upcomingSurgeryList = pd.DataFrame(requests.get(
        f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/5/A001/{
            upcomingSurgeryDate_str}"
    ).json())

    if not upcomingSurgeryList.empty:
        upcomingSurgeryList = upcomingSurgeryList[[
            'mrn', 'pname', 'room', 'cdo', 'operp', 'name', 'plandate']]
        upcomingSurgeryList = upcomingSurgeryList[upcomingSurgeryList['name'] == aName]
        upcomingSurgeryList.loc[:,
                                'mrn'] = upcomingSurgeryList['mrn'].astype(str)
    else:
        upcomingSurgeryList = pd.DataFrame(
            columns=['mrn', 'pname', 'room', 'cdo', 'operp', 'name', 'plandate'])

    # 叠加 prelastSurgeryList， lastSurgeryList，upcomingSurgeryList
    surgicalList = pd.concat(
        [prelastSurgeryList, lastSurgeryList, upcomingSurgeryList])

    # 删除plandate 列 包括“T"后面的所有字符
    surgicalList.loc[:, 'plandate'] = surgicalList['plandate'].str.split(
        'T').str[0]

    # %%
    # 将 arrangeDF 和 surgicalList 根据 mrn 和pname 列合并，要求保留所有行
    arrangeList = pd.merge(scheduleList, surgicalList,
                           on=['mrn', 'pname'], how='left')

    # arrangeList 保留 plandate为 NaN 或者 planDate 为 upcomingSurgeryDate 的行
    arrangeList = arrangeList[arrangeList['plandate'].isna() |
                              (arrangeList['plandate'] == upcomingSurgeryDate_str)]

    arrangeList = arrangeList[['room', 'cdo', 'pname', 'mrn', 'Isroom', 'diag',
                               'drremark', 'operp', 'PatientSex', 'PatientAge', 'AppOperativeDate', 'arrangedate', 'Doctor', 'bedid', 'plandate', ]]

    # 把arrangelist中的room列和cdo列改为字符串格式，并删除cdo列内容中的 .0
    arrangeList.loc[:, 'room'] = arrangeList['room'].astype(str)
    arrangeList.loc[:, 'cdo'] = arrangeList['cdo'].astype(str)
    arrangeList.loc[:, 'cdo'] = arrangeList['cdo'].str.split('.').str[0]

    # arrangeList 根据 room，cdo，AppOperateiveDate 升序排列
    arrangeList = arrangeList.sort_values(
        by=['room', 'cdo', 'AppOperativeDate'], ascending=[True, True, True])

    # %%
    arrangeList.to_excel(
        f"D:\\working-sync\\手术通知\\手术清单-{upcomingSurgeryDate}-{aName}.xlsx", index=False)

    # 定义文件名
    file_name = f"D:\\working-sync\\手术通知\\手术清单-{
        upcomingSurgeryDate}-{aName}.xlsx"

    # 使用 ExcelWriter 和 xlsxwriter 引擎
    with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
        arrangeList.to_excel(writer, sheet_name='Sheet1', index=False)

        # 获取 xlsxwriter 对象
        # workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        # 设置列宽度
        worksheet.set_column('A:A', 10)  # room
        worksheet.set_column('B:B', 10)  # cdo
        worksheet.set_column('C:C', 30)  # pname
        worksheet.set_column('D:D', 20)  # mrn
        worksheet.set_column('E:E', 20)  # Isroom
        worksheet.set_column('F:F', 100)  # diag
        worksheet.set_column('G:G', 100)  # drremark
        worksheet.set_column('H:H', 10)  # Sex
        worksheet.set_column('I:I', 10)  # Age
        worksheet.set_column('J:J', 30)  # AppOperativeDate
        worksheet.set_column('K:K', 30)  # arrangedate
        worksheet.set_column('L:L', 20)  # Doctor
        worksheet.set_column('M:M', 30)  # bedid
        worksheet.set_column('N:N', 30)  # plandate

    def highlight_upcomingSurgeryDate(row):
        if pd.notnull(row['AppOperativeDate']) and pd.to_datetime(row['AppOperativeDate']).date() == upcomingSurgeryDate:
            return ['background-color: yellow']*len(row)
        else:
            return ['']*len(row)

    def highlight_nextSurgeryDate(row):
        if pd.notnull(row['AppOperativeDate']) and pd.to_datetime(row['AppOperativeDate']).date() == nextSurgeyDate:
            return ['background-color: lightgreen']*len(row)
        else:
            return ['']*len(row)

    # 将列宽设置为table styles
    widthStyle = [
        {'selector': 'th.col_heading.level0.col0',
            'props': [('width', '40px')]},             # room
        {'selector': 'th.col_heading.level0.col1',
            'props': [('width', '40px')]},             # cdo
        {'selector': 'th.col_heading.level0.col2',
            'props': [('width', '80px')]},             # pname
        {'selector': 'th.col_heading.level0.col3',
            'props': [('width', '80px')]},             # mrn
        {'selector': 'th.col_heading.level0.col4',
            'props': [('width', '60px')]},             # Isroom
        {'selector': 'th.col_heading.level0.col5',
            'props': [('width', '200px')]},            # diag
        {'selector': 'th.col_heading.level0.col6',
            'props': [('width', '200px')]},            # drremark
        {'selector': 'th.col_heading.level0.col7',
            'props': [('width', '200px')]},            # operp
        {'selector': 'th.col_heading.level0.col8',
            'props': [('width', '50px')]},            # PatientSex
        {'selector': 'th.col_heading.level0.col9',
            'props': [('width', '50px')]},            # PatientAge
        {'selector': 'th.col_heading.level0.col10',
            'props': [('width', '100px')]},            # AppOperativeDate
        {'selector': 'th.col_heading.level0.col11',
            'props': [('width', '100px')]},            # arrangedate
        {'selector': 'th.col_heading.level0.col12',
            'props': [('width', '100px')]},            # Doctor
        {'selector': 'th.col_heading.level0.col13',
            'props': [('width', '100px')]},            # bedid
        {'selector': 'th.col_heading.level0.col14',
            'props': [('width', '100px')]}             # plandate
    ]

    # 定义固定列的样式
    columnFixStyle = [
        {'selector': 'tr:nth-child(odd) th:nth-child(1), tr:nth-child(odd) td:nth-child(1)',
            'props': 'position: -webkit-sticky; position: sticky; left:0px; background-color: #f6f6f6;'},
        {'selector': 'tr:nth-child(even) th:nth-child(1), tr:nth-child(even) td:nth-child(1)',
            'props': 'position: -webkit-sticky; position: sticky; left:0px; background-color: #ffffff;'},
        {'selector': 'tr:nth-child(odd) th:nth-child(2), tr:nth-child(odd) td:nth-child(2)',
            'props': 'position: -webkit-sticky; position: sticky; left:50px; background-color: #f6f6f6;'},
        {'selector': 'tr:nth-child(even) th:nth-child(2), tr:nth-child(even) td:nth-child(2)',
            'props': 'position: -webkit-sticky; position: sticky; left:50px; background-color: #ffffff;'},
        {'selector': 'tr:nth-child(odd) th:nth-child(3), tr:nth-child(odd) td:nth-child(3)',
            'props': 'position: -webkit-sticky; position: sticky; left:100px; background-color: #f6f6f6;'},
        {'selector': 'tr:nth-child(even) th:nth-child(3), tr:nth-child(even) td:nth-child(3)',
            'props': 'position: -webkit-sticky; position: sticky; left:100px; background-color: #ffffff;'},
    ]

    arrangeListHtml = arrangeList.style.hide().set_table_attributes('style="width:2000px;"').set_table_styles(
        widthStyle+columnFixStyle).apply(highlight_upcomingSurgeryDate, axis=1).apply(highlight_nextSurgeryDate, axis=1).to_html()

    return arrangeList, arrangeListHtml, upcomingSurgeryDate_str
