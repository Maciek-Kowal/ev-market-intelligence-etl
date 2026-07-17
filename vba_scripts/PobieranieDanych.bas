Attribute VB_Name = "PobieranieDanych"
Sub PobierzDaneZBigQuery()
    Dim conn As Object
    Dim rs As Object
    Dim sql As String
    Dim i As Integer
    Dim wsData As Worksheet
    Dim wsReport As Worksheet
    Dim ptCache As PivotCache
    Dim pt As PivotTable
    Dim dataRange As Range
    Dim lastRow As Long, lastCol As Long
    
    Set conn = CreateObject("ADODB.Connection")
    Set rs = CreateObject("ADODB.Recordset")
    conn.Open "DSN=Google BigQuery;"
    
    sql = "SELECT * FROM `otomoto-intelligence.prod_ev_intelligence.v_daily_raport`"
    rs.Open sql, conn
    
    On Error Resume Next
    Set wsData = Worksheets("Dane_Surowe")
    On Error GoTo 0
    
    If wsData Is Nothing Then
        Set wsData = Worksheets.Add(Before:=Worksheets(1))
        wsData.Name = "Dane_Surowe"
    End If

    wsData.Cells.Clear
    For i = 0 To rs.Fields.Count - 1
        wsData.Cells(1, i + 1).Value = rs.Fields(i).Name
    Next i
    wsData.Range("A2").CopyFromRecordset rs
    
    rs.Close
    conn.Close
    Set rs = Nothing
    Set conn = Nothing
    
    lastRow = wsData.Cells(wsData.Rows.Count, 1).End(xlUp).Row
    lastCol = wsData.Cells(1, wsData.Columns.Count).End(xlToLeft).Column
    Set dataRange = wsData.Range(wsData.Cells(1, 1), wsData.Cells(lastRow, lastCol))
    
    On Error Resume Next
    Application.DisplayAlerts = False
    Worksheets("Dashboard_EV").Delete
    Application.DisplayAlerts = True
    On Error GoTo 0
    
    Set wsReport = Worksheets.Add(After:=wsData)
    wsReport.Name = "Dashboard_EV"


    wsReport.Range("B1").Value = "Ostatnia aktualizacja:"
    wsReport.Range("C1").Value = Now
    wsReport.Range("B1:C1").Font.Bold = True
    wsReport.Range("C1").NumberFormat = "yyyy-mm-dd hh:mm"

    Set ptCache = ActiveWorkbook.PivotCaches.Create(SourceType:=xlDatabase, SourceData:=dataRange)
    Set pt = ptCache.CreatePivotTable(TableDestination:=wsReport.Range("B3"), TableName:="RaportEV")
    
    With pt
        With .PivotFields("make")
            .Orientation = xlRowField
            .Position = 1
        End With
        With .PivotFields("model")
            .Orientation = xlRowField
            .Position = 2
        End With
        With .PivotFields("url")
            .Orientation = xlDataField
            .Function = xlCount
            .Name = "Liczba aut na rynku"
        End With
        
        With .PivotFields("price")
            .Orientation = xlDataField
            .Function = xlAverage
            .NumberFormat = "# ##0 z³"
            .Name = "Œrednia Cena"
        End With
    End With
    
    wsReport.Columns("B:E").AutoFit
    
    MsgBox "Sukces! Pobrano najœwie¿sze dane z BigQuery i wygenerowano raport.", vbInformation, "ETL Sukces"
End Sub
