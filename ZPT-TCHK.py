from tkinter import *
from tkinter import filedialog
from tkinter import scrolledtext
from tkinter import ttk
from tkinter import font
import os
import xml.etree.ElementTree as ET



def delete():
    txt.delete(1.0, END)

def select_directory():  
    directory_path = filedialog.askdirectory(title="Выбрать папку")  
    return directory_path

def summDet():                              ### Функция подчитывает количество деталей по материалам, 
    direcFile = select_directory()          ### и сравнивает количетво файлов .pgmx с .csv
    detalCSV = {}
    nameDict = {}
    wor = 0
    summPGMX = 0
    keyOBOROT = []
    keyPusto = []
    for filename in os.listdir(direcFile):
        f = os.path.join(direcFile, filename)               # формирует путь к файлу
        if os.path.isfile(f) and filename.endswith('.csv'): # проверка файла что файл .csv
            fileRead = open(f, 'r', encoding='utf-8')       # открывает файл
            contentCSV = fileRead.read()                    # считывает инфу с файла
            contentCSV = contentCSV[:-1]
            contentCSVdet = contentCSV.split("\n")
            summ = 0
            for detal in contentCSVdet:                     # считает количество деталей в .csv
                detalSpl = detal.split(";")
                keys = str(detalSpl[0])
                values = detalSpl[1]
                keys = keys[18:]
                values = values[11:]
                #print (keys, values)
                detalCSV[keys] = values                
                summ += int(values)
            fileRead.close()
            filename =str(filename) +' = '+ str(summ) + ' шт.' +'\n'
            txt.insert(INSERT, str(filename)) 
            wor += 1
        elif os.path.isfile(f) and filename.endswith('.pgmx'): # проверка файла что файл .pgmx
            fName = os.path.basename(f)                         # считает количество деталей в .pgmx
            nameDict[fName] = 1
            summPGMX += 1
    summPGMX ='Всего файлов = '+ str(summPGMX) + ' шт.' +'\n\n'
    txt.insert(INSERT, str(summPGMX)) 
    
    if detalCSV.keys() == nameDict.keys():              # сравнивает список из .csv со списком .pgmx 
        txt.insert(INSERT, 'Все файлы есть. Оборотов нет!\n\n\n')
    else:
        a = detalCSV.keys() ^ nameDict.keys()
        countA = 0
        for key in a:
            if 'OBOROT'in key :                
                keyOBOROT.append(key)                
            else:
                keyPusto.append(key)
        keyOBOROT = sorted(keyOBOROT)
        keyPusto = sorted(keyPusto)
        for item in keyOBOROT:
            txt.insert(INSERT, item + '\n')
        for jitem in keyPusto:
            txt.insert(INSERT, '!ФАЙЛА НЕТ -- ' + jitem + '\n')
        countA += 1

def clickedReplace():                       ### Функция меняет в файлах .SCX для сверлилки все запятые на точки, так как станок не читает запятые
    direcFile = select_directory()
    countSCX = 1
    textCli = 0
    for filename in os.listdir(direcFile):        
        f = os.path.join(direcFile, filename)                   # формирует путь к файлу        
        if os.path.isfile(f) and filename.endswith('.SCX'):     # проверка файла что файл .SCX
            fileR = open(f, 'r', encoding='utf-8')              # открывает файл
            content = fileR.read()                              # считывает инфу с файла
            string = str(content)
            new_string = string.replace(",", ".")                   # меняет запятые на точки
            fileR.close() 
            fileW = open(f, 'w', encoding='utf-8')                  # открывает файл для записи инфы
            fileW.write(new_string)
            textCli = 'Запятых заменено в ' + str(countSCX) + ' файлов \n\n'
            countSCX = countSCX + 1
            fileW.close()
    txt.insert(INSERT, str(textCli))            

def pravkaSCX():                    ### Функция исправляет ошибки Базиса в файлах .SCX для сверлилки, и ищет панели не проходящие по ширине
    direcFile = select_directory()
    count = 1
    countW = 0
    textPravkaSCX = 0
    for filename in os.listdir(direcFile):
        f = os.path.join(direcFile, filename)                   # формирует путь к файлу
        if os.path.isfile(f) and filename.endswith('.SCX'):      # проверка файла что файл .SCX
            tree = ET.parse(f)
            root = tree.getroot()                                   # открываем файл, а затем получаем корневой элемент дерева XML.
            #print (os.path.basename(f))
            swith = 0
            for elem in root.findall('.//Machining'):       # ищет все елементы Machining
                if elem.attrib['Type'] == '1':
                    if elem.attrib['Diameter'] == '12.222': # проверяет диаметры (находим метку)
                        fase = elem.attrib['Face']          # считываем нужные параметры с метки
                        zet = elem.attrib['Z']
                        elem.clear()                        # удаляем параметры с метки
                        elem.set('Type', 'None')            # записываем пустые параметры
                        elem.set('Face', '0')
                        swith = 1
                elif elem.attrib['Type'] == '4':
                    if elem.attrib['Width'] == '12.6':  # находим паз и записываем в паз нужные параметры
                        wi = '12,6'
                        elem.set('Width', wi)
                    if swith == 1:
                        elem.set('Face', fase)
                        elem.set('Z', zet)
                        elem.set('EndZ', zet)
            for wid in root.findall('.//Panel'):            # ищет ширину детали, в свойствах (Panel)                
                if float(wid.attrib['Width']) >= 1200:
                    fNameW = os.path.basename(f)
                    fNameW ='деталь ' + str(fNameW) + ' не входит, ширина = ' + wid.attrib['Width'] +'\n'
                    txt.insert(INSERT, str(fNameW)) 
                    countW += 1
                else:
                    pass
            textPravkaSCX = 'Готово ' + str(count) + ' файлов \n\n' 
            count = count + 1
            tree.write(f, encoding="utf-8", xml_declaration=True)
    txt.insert(INSERT, str(textPravkaSCX)) 

window = Tk()
window.title("LITIUM")
window.geometry('1800x700')

font1 = font.Font(family= "Arial", size=16, weight="normal", slant="roman")
frame = ttk.Frame(borderwidth=1, padding=[10, 10])
frame.pack(side=TOP, fill=X, padx=5, pady=5)
btn0 = Button(frame, text="1) Проверить и исправить пазы", command=pravkaSCX, font=font1)
btn0.grid(row=0, column=0)
btn1 = Button(frame, text="2) Заменить запятые на точки", command=clickedReplace, font=font1)
btn1.grid(row=0, column=1)
btn2 = Button(frame, text="3) Подсчитать детали", command=summDet, font=font1)
btn2.grid(row=0, column=2)
btn3 = Button(frame, text="4) Очиcтить", command=delete, font=font1)
btn3.grid(row=0, column=3)
txt = scrolledtext.ScrolledText(window,width=100,height=50, font=font1)
txt.pack(fill=BOTH, anchor="center", padx=10, pady=10, expand=True)

window.mainloop()
# auto-py-to-exe