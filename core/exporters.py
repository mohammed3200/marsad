"""
marsad report exporters — PDF + Excel.

UI-agnostic standalone functions taking (results, output_path). Moved out of the
root package __init__ so the old root package can be removed. Both read the same
`results` dict (keyed by agent id) that the dashboard and connectors use.
"""
import os, datetime

def export_pdf(results: dict, output_path: str) -> str:
    from reportlab.lib.pagesizes   import A4
    from reportlab.lib             import colors
    from reportlab.lib.units       import cm
    from reportlab.platypus        import (
        SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, HRFlowable, PageBreak
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums  import TA_CENTER, TA_RIGHT

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm)

    DARK  = colors.HexColor("#0D1B2A")
    BLUE  = colors.HexColor("#1E3A5F")
    ACC   = colors.HexColor("#2563EB")
    GREEN = colors.HexColor("#065F46")
    RED   = colors.HexColor("#7F1D1D")
    WHITE = colors.white
    GRAY  = colors.HexColor("#F1F5F9")
    GLT   = colors.HexColor("#D1FAE5")
    RLT   = colors.HexColor("#FEE2E2")
    YLT   = colors.HexColor("#FEF3C7")
    BORD  = colors.HexColor("#CBD5E1")
    thin  = {"style": "GRID","colorName": "#CBD5E1","width": 0.5}

    def S(name, size=10, bold=False, color=colors.HexColor("#1E293B"),
          align=TA_RIGHT, leading=15):
        return ParagraphStyle(name, fontSize=size, textColor=color,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            alignment=align, leading=leading, spaceAfter=3)

    def sec_hdr(title, bg=ACC):
        return Table([[Paragraph(title, S("sh",13,True,WHITE,TA_CENTER))]],
            colWidths=[17.5*cm],
            style=TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),
                              ("TOPPADDING",(0,0),(-1,-1),9),
                              ("BOTTOMPADDING",(0,0),(-1,-1),9)]))

    chief  = results.get("chief",{})
    risk   = results.get("risk",{})
    sched  = results.get("schedule",{})
    fin    = results.get("cost",{})
    qual   = results.get("quality",{})
    health = chief.get("overall_health","غير محدد")
    hbg    = GREEN if health=="جيد" else colors.HexColor("#78350F") if health=="متوسط" else RED

    story = []

    # غلاف
    story.append(Table(
        [[Paragraph("نظام إدارة المشاريع الذكي — LTT 4G/5G",S("t",17,True,WHITE,TA_CENTER,22))],
         [Paragraph(f"تاريخ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    S("d",10,False,colors.HexColor("#94A3B8"),TA_CENTER))]],
        colWidths=[17.5*cm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1),DARK),
                          ("TOPPADDING",(0,0),(-1,-1),12),
                          ("BOTTOMPADDING",(0,0),(-1,-1),12)])))
    story.append(Spacer(1,.3*cm))
    story.append(Table([[Paragraph(f"الحالة العامة: {health}",S("h",14,True,WHITE,TA_CENTER,18))]],
        colWidths=[17.5*cm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1),hbg),
                          ("TOPPADDING",(0,0),(-1,-1),8),
                          ("BOTTOMPADDING",(0,0),(-1,-1),8)])))
    story.append(Spacer(1,.4*cm))

    # ملخص
    if chief.get("executive_summary"):
        story.append(sec_hdr("الملخص التنفيذي"))
        story.append(Spacer(1,.2*cm))
        story.append(Table([[Paragraph(chief["executive_summary"],S("b",10,leading=17))]],
            colWidths=[17.5*cm],
            style=TableStyle([("BACKGROUND",(0,0),(-1,-1),GRAY),
                              ("TOPPADDING",(0,0),(-1,-1),10),
                              ("BOTTOMPADDING",(0,0),(-1,-1),10),
                              ("LEFTPADDING",(0,0),(-1,-1),12),
                              ("BOX",(0,0),(-1,-1),1,BLUE)])))
        story.append(Spacer(1,.4*cm))

    # KPIs
    if chief.get("kpis"):
        story.append(sec_hdr("مؤشرات الأداء الرئيسية (KPIs)"))
        story.append(Spacer(1,.2*cm))
        kpi_data=[[Paragraph(h,S("kh",10,True,WHITE,TA_CENTER))
                   for h in ["المؤشر","القيمة","الاتجاه","الحالة"]]]
        for k in chief["kpis"]:
            s=k.get("status","")
            kpi_data.append([Paragraph(k.get("name",""),S("n")),
                             Paragraph(str(k.get("value","")),S("v",align=TA_CENTER)),
                             Paragraph(str(k.get("trend","")),S("tr",align=TA_CENTER)),
                             Paragraph(s,S("st",align=TA_CENTER))])
        t=Table(kpi_data,colWidths=[7*cm,4*cm,2.5*cm,4*cm])
        ts=[("BACKGROUND",(0,0),(-1,0),BLUE),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("GRID",(0,0),(-1,-1),.5,BORD),("TOPPADDING",(0,0),(-1,-1),7),
            ("BOTTOMPADDING",(0,0),(-1,-1),7)]
        for i,k in enumerate(chief["kpis"],1):
            s=k.get("status","")
            bg=GLT if s=="جيد" else YLT if s=="تحذير" else RLT
            ts.append(("BACKGROUND",(3,i),(3,i),bg))
        t.setStyle(TableStyle(ts))
        story.append(t)
        story.append(Spacer(1,.4*cm))

    # المخاطر
    risks=risk.get("risks",[])
    if risks:
        story.append(sec_hdr("سجل المخاطر",RED))
        story.append(Spacer(1,.2*cm))
        rdata=[[Paragraph(h,S("rh",10,True,WHITE,TA_CENTER))
                for h in ["المخاطرة","المستوى","الوصف","الحل"]]]
        lc={"عالية":RLT,"متوسطة":YLT,"منخفضة":GLT}
        for rk in risks:
            rdata.append([Paragraph(rk.get("title",""),S("rt",9)),
                          Paragraph(rk.get("level",""),S("rl",9,align=TA_CENTER)),
                          Paragraph(rk.get("description",""),S("rd",8)),
                          Paragraph(rk.get("solution",""),S("rs",8))])
        rt=Table(rdata,colWidths=[4*cm,2.5*cm,5.5*cm,5.5*cm])
        rts=[("BACKGROUND",(0,0),(-1,0),RED),("TEXTCOLOR",(0,0),(-1,0),WHITE),
             ("GRID",(0,0),(-1,-1),.4,BORD),("TOPPADDING",(0,0),(-1,-1),6),
             ("BOTTOMPADDING",(0,0),(-1,-1),6)]
        for i,rk in enumerate(risks,1):
            rts.append(("BACKGROUND",(1,i),(1,i),lc.get(rk.get("level",""),WHITE)))
        rt.setStyle(TableStyle(rts))
        story.append(rt)
        story.append(Spacer(1,.4*cm))

    story.append(PageBreak())

    # الجدول الزمني
    story.append(sec_hdr("الجدول الزمني"))
    story.append(Spacer(1,.2*cm))
    sdata=[
        [Paragraph("التأخير (يوم)",S("sl",10,True)),Paragraph(str(sched.get("delay_days","-")),S("sv",align=TA_CENTER))],
        [Paragraph("الإنهاء الأصلي",S("sl",10,True)),Paragraph(sched.get("original_end","-"),S("sv",align=TA_CENTER))],
        [Paragraph("الإنهاء الجديد",S("sl",10,True)),Paragraph(sched.get("new_end","-"),S("sv",align=TA_CENTER))],
    ]
    story.append(Table(sdata,colWidths=[8*cm,9.5*cm],
        style=TableStyle([("BACKGROUND",(0,0),(0,-1),GRAY),
                          ("GRID",(0,0),(-1,-1),.5,BORD),
                          ("TOPPADDING",(0,0),(-1,-1),8),
                          ("BOTTOMPADDING",(0,0),(-1,-1),8),
                          ("LEFTPADDING",(0,0),(-1,-1),10)])))
    story.append(Spacer(1,.4*cm))

    # المالية
    story.append(sec_hdr("الوضع المالي",GREEN))
    story.append(Spacer(1,.2*cm))
    fdata=[
        [Paragraph("الميزانية الإجمالية",S("fl",10,True)),Paragraph(fin.get("total_budget","-"),S("fv",align=TA_CENTER))],
        [Paragraph("المُنفَق",S("fl",10,True)),Paragraph(fin.get("spent","-"),S("fv",align=TA_CENTER))],
        [Paragraph("المتبقي",S("fl",10,True)),Paragraph(fin.get("remaining","-"),S("fv",align=TA_CENTER))],
        [Paragraph("نسبة الإنفاق",S("fl",10,True)),Paragraph(f'{fin.get("spent_pct",0)}%',S("fv",align=TA_CENTER))],
        [Paragraph("نسبة الانحراف",S("fl",10,True)),Paragraph(f'+{fin.get("deviation_pct",0)}%',S("fv",align=TA_CENTER))],
    ]
    story.append(Table(fdata,colWidths=[8*cm,9.5*cm],
        style=TableStyle([("BACKGROUND",(0,0),(0,-1),GRAY),
                          ("BACKGROUND",(1,4),(1,4),RLT),
                          ("GRID",(0,0),(-1,-1),.5,BORD),
                          ("TOPPADDING",(0,0),(-1,-1),8),
                          ("BOTTOMPADDING",(0,0),(-1,-1),8),
                          ("LEFTPADDING",(0,0),(-1,-1),10)])))
    story.append(Spacer(1,.4*cm))

    # خطة العمل
    actions=chief.get("top_actions",[])
    if actions:
        story.append(sec_hdr("خطة العمل الفورية",BLUE))
        story.append(Spacer(1,.2*cm))
        adata=[[Paragraph(h,S("ah",10,True,WHITE,TA_CENTER))
                for h in ["#","الإجراء","المسؤول","الموعد","التأثير"]]]
        for act in actions:
            adata.append([
                Paragraph(str(act.get("priority","")),S("ap",bold=True,align=TA_CENTER)),
                Paragraph(act.get("action",""),S("aa",9)),
                Paragraph(act.get("owner",""),S("ao",9,align=TA_CENTER)),
                Paragraph(act.get("deadline",""),S("ad",9,align=TA_CENTER)),
                Paragraph(act.get("impact",""),S("ai",8)),
            ])
        at=Table(adata,colWidths=[1.5*cm,6*cm,3*cm,2.5*cm,4.5*cm])
        at.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),BLUE),
                                ("TEXTCOLOR",(0,0),(-1,0),WHITE),
                                ("GRID",(0,0),(-1,-1),.5,BORD),
                                ("TOPPADDING",(0,0),(-1,-1),7),
                                ("BOTTOMPADDING",(0,0),(-1,-1),7),
                                ("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        story.append(at)

    # Footer
    story.append(Spacer(1,.8*cm))
    story.append(HRFlowable(width="100%",thickness=1,color=BLUE))
    story.append(Spacer(1,.2*cm))
    story.append(Paragraph(
        f"LTT PM Intelligence Desktop | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | سري",
        S("ft",8,False,colors.HexColor("#94A3B8"),TA_CENTER)))

    doc.build(story)
    return output_path


def export_excel(results: dict, output_path: str) -> str:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils  import get_column_letter

    wb  = Workbook()
    MID = "1E3A5F"; ACC = "2563EB"
    WHITE = "FFFFFF"; GRAY = "F1F5F9"; ALT = "EBF3FB"
    GRN = "D1FAE5"; RED = "FEE2E2"; YEL = "FEF3C7"
    BORD_C = "CBD5E1"

    def hdr(cell, bg=MID, fg=WHITE, bold=True, size=11):
        cell.font      = Font(bold=bold, color=fg, size=size, name="Arial")
        cell.fill      = PatternFill("solid", start_color=bg)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def body(cell, bold=False, color="1E293B", bg=None, center=False):
        cell.font      = Font(bold=bold, color=color, size=10, name="Arial")
        cell.alignment = Alignment(horizontal="center" if center else "right",
                                   vertical="center", wrap_text=True)
        if bg: cell.fill = PatternFill("solid", start_color=bg)

    def border_all(ws, r1, r2, c1, c2):
        s = Side(style="thin", color=BORD_C)
        b = Border(left=s, right=s, top=s, bottom=s)
        for row in ws.iter_rows(r1,r2,c1,c2):
            for cell in row: cell.border = b

    chief  = results.get("chief",{})
    risks  = results.get("risk",{}).get("risks",[])
    sched  = results.get("schedule",{})
    fin    = results.get("cost",{})
    qual   = results.get("quality",{})
    safety = results.get("safety",{})
    health = chief.get("overall_health","")
    hbg    = "065F46" if health=="جيد" else "78350F" if health=="متوسط" else "7F1D1D"
    hfg    = "6EE7B7" if health=="جيد" else "FCD34D" if health=="متوسط" else "FCA5A5"
    CW     = 9638

    # ═══ ورقة 1: لوحة التحكم ═══
    ws1 = wb.active; ws1.title="لوحة التحكم"; ws1.sheet_view.rightToLeft=True
    ws1.merge_cells("A1:G1"); hdr(ws1["A1"],"0D1B2A",WHITE,True,16)
    ws1["A1"].value = "نظام إدارة المشاريع الذكي — LTT 4G/5G — المنطقة الوسطى"
    ws1.row_dimensions[1].height=40
    ws1.merge_cells("A2:G2"); hdr(ws1["A2"],"0D1B2A","94A3B8",False,10)
    ws1["A2"].value = f"تاريخ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws1.merge_cells("A4:G4"); hdr(ws1["A4"],hbg,hfg,True,14)
    ws1["A4"].value = f"الحالة العامة:  {health}"
    ws1.row_dimensions[4].height=32

    # الملخص
    ws1.merge_cells("A6:G6"); hdr(ws1["A6"],ACC,WHITE,True,12)
    ws1["A6"].value = "الملخص التنفيذي"
    ws1.merge_cells("A7:G9"); body(ws1["A7"],bg=GRAY)
    ws1["A7"].value = chief.get("executive_summary","")
    ws1["A7"].alignment = Alignment(horizontal="right",vertical="top",wrap_text=True)
    ws1.row_dimensions[7].height=70

    # KPIs
    r=11
    ws1.merge_cells(f"A{r}:G{r}"); hdr(ws1[f"A{r}"],ACC,WHITE,True,12)
    ws1[f"A{r}"].value="مؤشرات الأداء"
    for ci,h in enumerate(["المؤشر","القيمة","الاتجاه","الحالة"],1):
        hdr(ws1.cell(r+1,ci),MID); ws1.cell(r+1,ci).value=h
    for i,kpi in enumerate(chief.get("kpis",[]),r+2):
        s=kpi.get("status","")
        bg=GRN if s=="جيد" else YEL if s=="تحذير" else RED
        for ci,v in enumerate([kpi.get("name",""),kpi.get("value",""),kpi.get("trend",""),s],1):
            c=ws1.cell(i,ci); c.value=v
            body(c,bold=(ci==4),
                 color="065F46" if s=="جيد" and ci==4 else "92400E" if s=="تحذير" and ci==4 else "991B1B" if ci==4 else "1E293B",
                 bg=bg if ci==4 else (GRAY if i%2==0 else WHITE),center=(ci>1))
    for ci,w in enumerate([30,15,10,15,20,15,15],1):
        ws1.column_dimensions[get_column_letter(ci)].width=w

    # خطة العمل
    act_start=r+2+len(chief.get("kpis",[]))+2
    ws1.merge_cells(f"A{act_start}:G{act_start}"); hdr(ws1[f"A{act_start}"],MID,WHITE,True,12)
    ws1[f"A{act_start}"].value="خطة العمل الفورية"
    for ci,h in enumerate(["#","الإجراء","المسؤول","الموعد","التأثير","الإدارة"],1):
        hdr(ws1.cell(act_start+1,ci),MID); ws1.cell(act_start+1,ci).value=h
    pbgs=["7F1D1D","78350F","1E3A5F"]
    for i,act in enumerate(chief.get("top_actions",[]),act_start+2):
        p=min(act.get("priority",1)-1,2); bg=pbgs[p]
        for ci,v in enumerate([str(act.get("priority","")),act.get("action",""),act.get("owner",""),
                                act.get("deadline",""),act.get("impact",""),act.get("dept","")],1):
            c=ws1.cell(i,ci); c.value=v
            body(c,bold=(ci==1),
                 color="FCA5A5" if ci==1 and p==0 else "FCD34D" if ci==1 and p==1 else "93C5FD" if ci==1 else "1E293B",
                 bg=bg if ci==1 else (GRAY if i%2==0 else WHITE),center=(ci==1))
        ws1.row_dimensions[i].height=22

    # ═══ ورقة 2: المخاطر ═══
    ws2=wb.create_sheet("المخاطر"); ws2.sheet_view.rightToLeft=True
    ws2.merge_cells("A1:F1"); hdr(ws2["A1"],"0D1B2A",WHITE,True,13)
    ws2["A1"].value="سجل المخاطر الشامل"; ws2.row_dimensions[1].height=32
    for ci,(h,w) in enumerate(zip(["المخاطرة","المستوى","الفئة","الوصف","الحل","المسؤول"],
                                   [25,14,14,38,38,20]),1):
        hdr(ws2.cell(2,ci),MID); ws2.cell(2,ci).value=h
        ws2.column_dimensions[get_column_letter(ci)].width=w
    lv={"عالية":("7F1D1D","FCA5A5"),"متوسطة":("78350F","FCD34D"),"منخفضة":("064E3B","6EE7B7")}
    for ri,rk in enumerate(risks,3):
        l=rk.get("level",""); bg,fg=lv.get(l,("1E293B",WHITE))
        for ci,v in enumerate([rk.get("title",""),l,rk.get("category",""),
                                rk.get("description",""),rk.get("solution",""),rk.get("owner","")],1):
            c=ws2.cell(ri,ci); c.value=v
            body(c,bold=(ci==2),color=fg if ci==2 else "1E293B",
                 bg=bg if ci==2 else (GRAY if ri%2==0 else WHITE),center=(ci==2))
        ws2.row_dimensions[ri].height=28

    # ═══ ورقة 3: الجدول الزمني ═══
    ws3=wb.create_sheet("الجدول الزمني"); ws3.sheet_view.rightToLeft=True
    ws3.merge_cells("A1:D1"); hdr(ws3["A1"],"0D1B2A",WHITE,True,13)
    ws3["A1"].value="الجدول الزمني للمشروع"; ws3.row_dimensions[1].height=32
    for ri,(l,v,vbg) in enumerate([("التأخير (يوم)",sched.get("delay_days","-"),"FEE2E2"),
                                    ("الإنهاء الأصلي",sched.get("original_end","-"),GRAY),
                                    ("الإنهاء الجديد",sched.get("new_end","-"),"FEF3C7")],2):
        body(ws3.cell(ri,1),True,bg=GRAY); ws3.cell(ri,1).value=l
        body(ws3.cell(ri,2),True,bg=vbg,center=True); ws3.cell(ri,2).value=str(v)
        ws3.row_dimensions[ri].height=24
    ws3.column_dimensions["A"].width=28; ws3.column_dimensions["B"].width=22
    r2=6; ws3.merge_cells(f"A{r2}:D{r2}"); hdr(ws3[f"A{r2}"],ACC,WHITE,True,11)
    ws3[f"A{r2}"].value="مراحل المشروع"
    for ci,(h,w) in enumerate(zip(["المرحلة","الحالة","الإنجاز (%)","الإدارة المسؤولة"],
                                   [28,16,18,30]),1):
        hdr(ws3.cell(r2+1,ci),MID); ws3.cell(r2+1,ci).value=h
        ws3.column_dimensions[get_column_letter(ci)].width=w
    for ri,ph in enumerate(sched.get("phases",[]),r2+2):
        s=ph.get("status",""); sbg=GRN if s=="مكتمل" else RED if s=="متأخر" else YEL
        for ci,v in enumerate([ph.get("name",""),s,f'{ph.get("completion_pct",0)}%',
                                ph.get("responsible_dept","")],1):
            c=ws3.cell(ri,ci); c.value=v
            body(c,bold=(ci==2),
                 color="065F46" if s=="مكتمل" and ci==2 else "991B1B" if s=="متأخر" and ci==2 else "92400E" if ci==2 else "1E293B",
                 bg=sbg if ci==2 else (GRAY if ri%2==0 else WHITE),center=(ci>1))
        ws3.row_dimensions[ri].height=22

    # ═══ ورقة 4: المالية ═══
    ws4=wb.create_sheet("المالية"); ws4.sheet_view.rightToLeft=True
    ws4.merge_cells("A1:C1"); hdr(ws4["A1"],"0D1B2A",WHITE,True,13)
    ws4["A1"].value="الوضع المالي"; ws4.row_dimensions[1].height=32
    for ri,(l,v,bg) in enumerate([
        ("الميزانية الإجمالية",fin.get("total_budget","-"),"D1FAE5"),
        ("المُنفَق",fin.get("spent","-"),"DBEAFE"),
        ("المتبقي",fin.get("remaining","-"),"E0F2FE"),
        ("نسبة الإنفاق",f'{fin.get("spent_pct",0)}%',GRAY),
        ("نسبة الانحراف",f'+{fin.get("deviation_pct",0)}%',"FEE2E2"),
        ("الدفعة القادمة",fin.get("next_payment","-"),GRAY),
    ],2):
        ws4.row_dimensions[ri].height=24
        body(ws4.cell(ri,1),True,bg=GRAY); ws4.cell(ri,1).value=l
        body(ws4.cell(ri,2),True,bg=bg,center=True); ws4.cell(ri,2).value=str(v)
    ws4.column_dimensions["A"].width=28; ws4.column_dimensions["B"].width=22

    # ═══ ورقة 5: الجودة والسلامة ═══
    ws5=wb.create_sheet("الجودة والسلامة"); ws5.sheet_view.rightToLeft=True
    ws5.merge_cells("A1:C1"); hdr(ws5["A1"],"0D1B2A",WHITE,True,13)
    ws5["A1"].value="تقرير الجودة والسلامة"; ws5.row_dimensions[1].height=32
    for ri,(l,v,bg) in enumerate([
        ("محطات فُحصت",qual.get("inspected","-"),GRAY),
        ("اجتازت المعيار",qual.get("passed","-"),GRN),
        ("تحتاج مراجعة",qual.get("failed","-"),RED),
        ("نسبة النجاح",f'{qual.get("pass_rate",0)}%',GRN),
        ("حوادث السلامة",safety.get("incidents","-"),RED),
        ("درجة السلامة",f'{safety.get("safety_score",0)}%',GRN),
    ],2):
        ws5.row_dimensions[ri].height=24
        body(ws5.cell(ri,1),True,bg=GRAY); ws5.cell(ri,1).value=l
        body(ws5.cell(ri,2),True,bg=bg,center=True); ws5.cell(ri,2).value=str(v)
    ws5.column_dimensions["A"].width=28; ws5.column_dimensions["B"].width=20

    wb.save(output_path)
    return output_path
