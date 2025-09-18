; AutoHotkey v2 代码，用于读取CSV文件并提取特定列的数据

#SingleInstance Force

; F11 重启
F11:: Reload


; 设置Ctrl+F3为启动快捷键
^F3::
{
    ProcessCSV()
    return
}

; 定义处理CSV文件的函数
ProcessCSV() {
    ; 定义CSV文件路径
    csvFilePath := "d:\MedTracker\otology-database\examination_record.csv"

    ; 检查文件是否存在
    if !FileExist(csvFilePath) {
        MsgBox "CSV文件不存在: " . csvFilePath
        return
    }

    ; 打开文件进行读取
    csvfile := FileOpen(csvFilePath, "r", "UTF-8")

    ; 读取表头行
    headerLine := csvfile.ReadLine()

    ; 使用逗号分割表头，获取列索引
    headers := StrSplit(headerLine, ",")

    ; 查找目标列的索引
    repoIndex := -1
    picdirIndex := -1
    picnameIndex := -1

    for index, header in headers {
        if (header = "repo")
            repoIndex := index
        else if (header = "picdir")
            picdirIndex := index
        else if (header = "picname")
            picnameIndex := index
    }

    ; 检查是否找到了所有需要的列
    if (repoIndex = -1 || picdirIndex = -1 || picnameIndex = -1) {
        MsgBox "CSV文件中缺少必要的列（repo、picdir或picname）"
        csvfile.Close()
        return
    }

    ; 下载前准备
    Sleep 1000
    Click 34, 177
    Click 99, 177
    Sleep 500
    Click 97, 425 ; 选择检查号
    Sleep 500
    Click 582, 177 ; 取消时间范围

    ; 逐行读取并处理数据
    while !csvfile.AtEOF {
        ; 读取一行数据
        line := csvfile.ReadLine()

        ; 如果行为空，跳过
        if (line = "")
            continue

        ; 分割数据行
        data := StrSplit(line, ",")

        ; 提取并存储所需列的数据
        repo := data[repoIndex]
        picdir := data[picdirIndex]
        picname := data[picnameIndex]

        ; 输入检查号
        Click 136, 176, 2
        Sleep 500
        Send repo
        Sleep 500
        Send "{Enter}"
        Sleep 5000

        Click 1177, 283 ; 点击下载
        Sleep 5000
        SendText "D:\otology-pic\" . picdir . "\" . picname . ".jpg"
        Sleep 1000
        Send "{Enter}"
        Sleep 2000
        Send "+{Tab}"
        Sleep 500
        Send "{Enter}"
        sleep 5000

        ; 或者在控制台显示（如果运行在控制台模式下）
        ; OutputDebug "repo: " . repo . "\npicdir: " . picdir . "\npicname: " . picname . "\n"
    }

    ; 关闭文件
    csvfile.Close()

    MsgBox "CSV文件处理完成！", "完成"
}