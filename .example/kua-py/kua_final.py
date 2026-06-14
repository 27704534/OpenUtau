# -*- coding: utf-8 -*-
import sys
import os
import re
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter import ttk
from tkinter import filedialog

print("loading...")
# print("应该没人看黑框框吧")
print("https://b23.tv/QqrzsnF")
# print("中华人民共和国万岁_世界人民大团结万岁")

"""
这是一个utau的歌词映射替换插件，并且有权重分配以及简单的衔接处理
"""

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

'''
映射表格式：分号分隔歌词和所要替换的拆音方案，分号后部分用下划线分隔不同的替换方案，逗号分隔不同音素，点分隔占比和音素
歌词;占比十分之几.音素,占比十分之几.音素_占比十分之几.音素,占比十分之几.音素
例如：
cao;3.tsu,4.a,3.o_6.cha,4.o
ce;10.cha
cen;7.che,3.n
'''
class MappingManager:
    def __init__(self):
        self.mapping_path = os.path.join(PLUGIN_DIR, "pinyin.txt")
        self.mapping = self._load_mapping()

    def _load_mapping(self, mapping_path=None):
        if mapping_path:
            self.mapping_path = mapping_path
        mapping = {}
        try:
            with open(self.mapping_path, 'r', encoding='utf-8') as f: #映射表使用utf8
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or ';' not in line:
                        continue
                    try:
                        pinyin, romaji = line.split(';', 1)
                        pinyin = pinyin.strip()
                        if not pinyin or not romaji:
                            continue
                        options = [opt.split(',') for opt in romaji.split('_') if opt]
                        if not options:
                            continue
                        formatted_options = []
                        for opt in options:
                            formatted_opt = []
                            valid_option = False
                            for part in opt:
                                if '.' in part:
                                    try:
                                        ratio, roma = part.split('.', 1)
                                        ratio = int(ratio)
                                        roma = roma.strip()
                                        if ratio <= 0 or not roma:
                                            continue
                                        formatted_opt.append((ratio, roma))
                                        valid_option = True
                                    except (ValueError, IndexError):
                                        continue
                                else:
                                    continue
                            if valid_option and formatted_opt:
                                formatted_options.append(formatted_opt)
                        if formatted_options:
                            mapping[pinyin] = formatted_options
                    except Exception:
                        continue
            return mapping if mapping else None
        except Exception as e:
            messagebox.showerror("映射表错误", "加载失败：{0}".format(str(e)))
            return None

r'''
以下内容引用自utau插件开发文档
[原文链接（日语）](https://w.atwiki.jp/utaou/pages/64.html) 作者：[UTAU ユーザー互助会@ ウィキ](https://w.atwiki.jp/utaou/)
UTAU本体会将选择范围的信息用临时文件输出后，将该文件路径通过插件的命令行调用参数传递。
插件通过读取该文件来获取音符信息。
插件在编辑选择范围的信息后，将结果覆盖输入的临时文件。
从UTAU传递的临时文件是由多个名为节的单位构成的文本格式。
文字编码为ShiftJIS，换行为CR+LF.
节内有存储音符的详细信息的被称作条目的东西。

### 节
指从[#●]开始直到下一个[#●]之前为止中间的部分。
基本上，一个节对应一个音符。
节有几个种类，各自的作用不同。
#### [#SETTING]
是存在于临时文件的最前面的节，记载有基本设定。
作为只读，即使变更对于本体侧的信息也不会有任何改变。
输出时，省略也没关系。
`Tempo` 曲速
`VoiceDir` 音源文件夹
`CacheDir` 缓存文件夹
`UstVersion` 插件用临时文件的版本（针对UTAU Ver.0.4以后，仅在开启设定的“以旧形式条目输出UST文件和插件脚本”时存在）
#### [#数字]
是记载选择范围的信息的节。
此节不能省略。
作为例外，插件操作被其本身取消时，可以省略任何节。
而且，节的数字没有意义，会根据输出顺序应用于本体的选择范围。
#### `[#PREV]`, `[#NEXT]`
`[#PREV]`存储选择范围前一音符的数据。
`[#NEXT]`中存有选择范围后一音符的数据。
若无前后音符，则没有此节。
输出时，省略也没关系，但如果不省略，就会反映出信息。
并且输出时，未必一定要写在紧邻数字节的前后。
#### `[#INSERT]`
是在输出时才能够使用的特别的节。
在它被写的位置追加音符。
因为被当作数字节的一种，所以即使写在`[#PREV]`前或`[#NEXT]`后，也不会在选择范围以外的位置追加音符。
并且，在选择范围后没有音符且选择范围末尾追加此节的情况下，若未恰当的指定Length，将产生长度0的音符，请注意。
#### [#DELETE]
是在输出时才能够使用的特别的节。
若以此替换数字节，会删除该音符。
不能删除其他的节。
#### [#VERSION]
是从UTAU0.4追加的节。
仅在UTAU设定中“以旧形式条目输出UST文件和插件脚本”开启的情况下存在。
截至目前只写作“UST Version 1.20”。
### 条目
条目在输出时可以省略，此时被UTAU侧解释为该条目内无变更。
因此，无变更音符可只返回节头。
在省略用`[#INSERT]`插入的节的条目的情况下，UTAU本体会填入某些值。此值和作为音符默认设定的值不同。
所谓条目的各说明中的“默认值”是使用`[#INSERT]`节追加音符的情况下，不指定任何条目时填入的值。
例如下面的
[#SETTING]
UstVersion=1.00
Project=D:\utau_use\project\zhi,pa,bu,di,kang.ust
Tempo=240.00
VoiceDir=D:\UTAU0419\UTAU0419\voice\New Geping UTAU Database
CacheDir=D:\utau_use\project\zhi,pa,bu,di,kang.cache
Mode2=True
[#PREV]
Length=960
Lyric=chui
NoteNum=64
PreUtterance=
Intensity=100
Moduration=0
Tempo=240.00
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=114.213
@overlap=-4.589
@stpoint=0
@filename=chui.wav
[#0001]
Length=960
Lyric=qi
NoteNum=64
PreUtterance=
Intensity=100
Moduration=0
Envelope=0,5,35,0,100,100,0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=141
@overlap=-5.999
@stpoint=0
@filename=qi.wav
[#0002]
Length=480
Lyric=xiao
NoteNum=64
PreUtterance=
Intensity=100
Moduration=0
Envelope=0,5,80,0,100,100,0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=161
@overlap=59.916
@stpoint=0
@filename=xiao.wav
[#0003]
Length=480
Lyric=ao
NoteNum=62
PreUtterance=
VoiceOverlap=80
Intensity=100
Moduration=0
Envelope=0,80,35,0,100,100,0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=9.507
@overlap=80
@stpoint=0
@filename=ao.wav
[#0004]
Length=960
Lyric=la
NoteNum=60
PreUtterance=
Intensity=100
Moduration=0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=44
@overlap=18
@stpoint=0
@filename=la.wav
[#0005]
Length=1920
Lyric=ba
NoteNum=62
PreUtterance=
Intensity=100
Moduration=0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=8.42
@overlap=-5.359
@stpoint=0
@filename=ba.wav
[#0006]
Length=480
Lyric=da
NoteNum=57
PreUtterance=
Intensity=100
Moduration=0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=13.999
@overlap=-3.371
@stpoint=0
@filename=da.wav
[#0007]
Length=480
Lyric=di
NoteNum=64
PreUtterance=
Intensity=100
Moduration=0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=16.999
@overlap=-3.962
@stpoint=0
@filename=di.wav
[#0008]
Length=480
Lyric=da
NoteNum=57
PreUtterance=
Intensity=100
Moduration=0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=13.999
@overlap=-3.371
@stpoint=0
@filename=da.wav
[#0009]
Length=480
Lyric=di
NoteNum=64
PreUtterance=
Intensity=100
Moduration=0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=16.999
@overlap=-3.962
@stpoint=0
@filename=di.wav
[#0010]
Length=1920
Lyric=da
NoteNum=62
PreUtterance=
Intensity=100
Moduration=0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=13.999
@overlap=-3.371
@stpoint=0
@filename=da.wav
[#NEXT]
Length=960
Lyric=da
NoteNum=60
PreUtterance=
Intensity=100
Moduration=0
PBW=50,50,50,50,50
PBY=0,0,0,0
PBS=0
@preuttr=13.999
@overlap=-3.371
@stpoint=0
@filename=da.wav
'''

class UstProcessor:
    def __init__(self, ust_path):
        self.ust_path = ust_path
        self.sections = []
        self._parse_ust()

    def _parse_ust(self):
        current_section = None
        try:
            with open(self.ust_path, 'r', encoding='shift_jis', errors='ignore') as f: #utau生成的临时ust是shift-jis编码的
                for line in f:
                    line = line.strip()
                    if line.startswith('[#'):
                        current_section = {
                            'header': line,
                            'type': self._get_section_type(line),
                            'data': {},
                            'original_index': len(self.sections)
                        }
                        self.sections.append(current_section)
                    elif current_section and '=' in line:
                        try:
                            key, value = line.split('=', 1)
                            current_section['data'][key.strip()] = value.strip()
                        except ValueError:
                            continue
        except Exception as e:
            messagebox.showerror("解析错误", "命令行传递参数解析失败：{0}".format(str(e)))

    def _get_section_type(self, header):
        match = re.match(r'\[#(\d+|PREV|NEXT)\]', header)
        if match:
            return 'number' if match.group(1).isdigit() else match.group(1)
        return 'other'

    def save(self, sections):
        try:
            with open(self.ust_path, 'w', encoding='shift_jis', newline='\r\n', errors='ignore') as f:
                for section in sections:
                    f.write(section['header'] + '\r\n')
                    for k, v in section['data'].items():
                        f.write('{0}={1}\r\n'.format(k, v))
            return True
        except Exception as e:
            messagebox.showerror("保存错误", "参数保存失败：{0}".format(str(e)))
            return False


class CompletionWindow(tk.Toplevel):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.title("完成")
        
        # 设置窗口图标
        icon_path = os.path.join(PLUGIN_DIR, "icon_64_64.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass  # 如果图标加载失败则忽略
        
        # 创建主框架
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # 添加图片和文字
        img_frame = tk.Frame(main_frame)
        img_frame.pack(side='top', fill='x')
        
        # 尝试加载GIF图片
        img_path = os.path.join(PLUGIN_DIR, "icon_128_128.gif")
        self.img = None
        if os.path.exists(img_path):
            try:
                self.img = tk.PhotoImage(file=img_path)
                img_label = tk.Label(img_frame, image=self.img)
                img_label.pack(side='left', padx=(0, 20))
            except Exception:
                pass  # 如果图片加载失败则忽略
        
        # 添加文字
        text_frame = tk.Frame(img_frame)
        text_frame.pack(side='left', fill='y', expand=True)
        
        tk.Label(text_frame, text=message, font=("Arial", 12)).pack(pady=5)
        tk.Label(text_frame, text="操作已成功完成", font=("Arial", 10)).pack(pady=5)
        
        # 添加确定按钮
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side='bottom', fill='x', pady=(20, 0))
        
        tk.Button(button_frame, text="确定", command=self.destroy, width=15).pack()
        
        # 设置窗口大小和位置
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        # 修复Python 3.4兼容性问题 - 使用字符串格式化代替f-strings
        self.geometry("+{}+{}".format(x, y))
        
        # 设置为模态窗口
        self.transient(parent)
        self.grab_set()
        self.wait_window(self)


class MappingInterface:
    def __init__(self, master, sections, mapping_manager, ust_path):
        self.master = master
        self.original_sections = sections
        self.mapping_manager = mapping_manager
        self.ust_path = ust_path
        self.modified_sections = []
        self.selections = {}
        self.current_combobox = None
        self.overlap_var = tk.BooleanVar(value=True)
        self.overlap_entry = tk.StringVar(value='80')
        self.pre_utterance_var = tk.BooleanVar(value=False)

        # 设置主窗口图标
        icon_path = os.path.join(PLUGIN_DIR, "icon_64_64.ico")
        if os.path.exists(icon_path):
            try:
                self.master.iconbitmap(icon_path)
            except Exception:
                pass  # 如果图标加载失败则忽略

        master.title("映射替换拆音工具")
        self._setup_ui()

    def _setup_ui(self):
        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        # 使用 grid 布局
        main_frame.grid_columnconfigure(0, weight=1)  # 左侧动态扩展
        main_frame.grid_columnconfigure(1, weight=0)  # 右侧固定

        # 勾选框和输入框（左侧）
        ctrl_frame = tk.Frame(main_frame)
        ctrl_frame.grid(row=0, column=0, sticky='w')

        overlap_frame = tk.Frame(ctrl_frame)
        ttk.Checkbutton(overlap_frame, text="衔接处 overlap (ms)", variable=self.overlap_var).pack(side='left')
        ttk.Entry(overlap_frame, textvariable=self.overlap_entry, width=6).pack(side='left', padx=5)
        overlap_frame.pack(side='top', fill='x', pady=2)

        ttk.Checkbutton(ctrl_frame, text="设置PreUtterance为0", variable=self.pre_utterance_var).pack(side='top', fill='x', pady=2)

        # 按钮和映射表文件名（右侧）
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=0, column=1, padx=10, sticky='e')  # 向右偏移 10 像素

        ttk.Button(button_frame, text="选择映射表", command=self._select_mapping_file).pack(side='left', padx=5)
        ttk.Button(button_frame, text="应用替换", command=self._apply_changes).pack(side='left', padx=5)

        self.mapping_label = ttk.Label(main_frame, text="当前映射表：{0}".format(os.path.basename(self.mapping_manager.mapping_path)))
        self.mapping_label.grid(row=1, column=1, sticky='e', pady=5)

        # Treeview
        self.tree = ttk.Treeview(
            main_frame,
            columns=('type', 'lyric', 'options'),
            show='headings',
            selectmode='none'
        )
        self.tree.heading('type', text='类型')
        self.tree.heading('lyric', text='原拼音')
        self.tree.heading('options', text='替换方案')
        self.tree.column('type', width=100, anchor='center')
        self.tree.column('lyric', width=150, anchor='center')
        self.tree.column('options', width=350, anchor='w')

        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=2, column=0, columnspan=2, sticky='nsew')
        scrollbar.grid(row=2, column=2, sticky='ns')

        self.tree.bind("<Double-1>", self._on_double_click)

        self._populate_tree()

    def _select_mapping_file(self):
        while True:
            file_path = filedialog.askopenfilename(
                title="选择映射表文件",
                filetypes=[("Text files", "*.txt")],
                initialdir=PLUGIN_DIR
            )
            if not file_path:
                break  # 用户取消选择

            new_mapping = self.mapping_manager._load_mapping(file_path)
            if new_mapping:
                self.mapping_manager.mapping = new_mapping
                self.mapping_label.config(text="当前映射表：{0}".format(os.path.basename(file_path)))
                self.selections.clear()
                self.tree.delete(*self.tree.get_children())
                self._populate_tree()
                break
            else:
                messagebox.showerror("错误", "映射表格式错误，请重新选择")

    def _populate_tree(self):
        for idx, section in enumerate(self.original_sections):
            if section['type'] != 'number':
                self._add_uneditable_row(section)
                continue

            lyric = section['data'].get('Lyric', '')
            if lyric == 'R':
                self.tree.insert('', 'end', values=('休止符', lyric, '--'), tags=('uneditable',))
            elif lyric in self.mapping_manager.mapping and len(self.mapping_manager.mapping[lyric]) > 0:
                options = self.mapping_manager.mapping[lyric]
                default_option = ', '.join(roma for _, roma in options[0])
                self.selections[idx] = options[0]
                self.tree.insert('', 'end', values=('可替换', lyric, default_option), tags=('editable',))
            else:
                self.tree.insert('', 'end', values=('无匹配', lyric, '--'), tags=('no_match_non_r',))

        self.tree.tag_configure('editable', background='#f0f0ff')
        self.tree.tag_configure('uneditable', background='#f0f0f0')
        self.tree.tag_configure('no_match_non_r', foreground='red', background='#f0f0f0')

    def _add_uneditable_row(self, section):
        display_type = {
            'PREV': '前导音符',
            'NEXT': '后续音符',
            'other': '其他'
        }.get(section['type'], '特殊')
        lyric = section['data'].get('Lyric', section['type'])
        self.tree.insert('', 'end', values=(display_type, lyric, '（不可修改）'), tags=('uneditable',))

    def _on_double_click(self, event):
        if self.current_combobox:
            self.current_combobox.destroy()

        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or col_id != '#3':
            return

        item = self.tree.item(row_id)
        if 'editable' not in self.tree.item(row_id, 'tags'):
            return

        idx = self.tree.index(row_id)
        lyric = item['values'][1]
        options = self.mapping_manager.mapping.get(lyric, [])

        bbox = self.tree.bbox(row_id, col_id)
        if not bbox:
            return

        self.current_combobox = ttk.Combobox(
            self.tree,
            values=[', '.join(roma for _, roma in opt) for opt in options],
            state='readonly',
            width=45
        )
        self.current_combobox.set(item['values'][2])
        self.current_combobox.place(
            x=bbox[0],
            y=bbox[1],
            width=bbox[2],
            height=bbox[3]
        )
        self.current_combobox.bind(
            "<<ComboboxSelected>>",
            lambda e, r=row_id, i=idx: self._update_selection(r, i)
        )

    def _update_selection(self, row_id, original_idx):
        selected = self.current_combobox.get()
        options = self.mapping_manager.mapping.get(self.tree.item(row_id)['values'][1], [])
        for opt in options:
            if ', '.join(roma for _, roma in opt) == selected:
                self.selections[original_idx] = opt
                break
        self.tree.set(row_id, 'options', selected)
        self.current_combobox.destroy()
        self.current_combobox = None

    def _apply_changes(self):
        try:
            overlap_value = int(self.overlap_entry.get())
            if overlap_value <= 0:
                messagebox.showerror("错误", "overlap 值必须为正整数")
                return
        except ValueError:
            messagebox.showerror("错误", "请输入有效的 overlap 值（正整数）")
            return

        new_sections = []
        for idx, section in enumerate(self.original_sections):
            if section['type'] != 'number':
                new_sections.append(section)
                continue

            if idx not in self.selections:
                new_sections.append(section)
                continue

            original_note = section
            romaji_list = self.selections[idx]
            new_notes = self._generate_new_notes(original_note, romaji_list, overlap_value)
            new_sections.extend(new_notes)
            new_sections.append({
                'header': '[#DELETE]',
                'type': 'number',
                'data': section['data'].copy()
            })

        if UstProcessor(self.ust_path).save(new_sections):
            # 使用自定义完成提示窗口
            CompletionWindow(self.master, "替换操作已完成喵")
            self.master.destroy()

    def _generate_new_notes(self, original_note, romaji_list, overlap_value):
        new_notes = []
        total_length = int(original_note['data'].get('Length', 480))
        total_ratio = sum(ratio for ratio, _ in romaji_list) or 10

        for i, (ratio, roma_sound) in enumerate(romaji_list):
            note_length = int(total_length * ratio / total_ratio)
            if note_length <= 0:
                continue

            new_note = {
                'header': '[#INSERT]',
                'type': 'number',
                'data': {
                    'Lyric': roma_sound,
                    'Length': str(note_length),
                    'NoteNum': original_note['data'].get('NoteNum', '60'),
                    'PreUtterance': '0' if self.pre_utterance_var.get() else ' ', #若勾选，则填入0，这样可以有效减少utau中因包络线重叠报错，但是同时会影响发音：若不勾选，填入空值
                    'VoiceOverlap': str(overlap_value) if self.overlap_var.get() and i > 0 else ' ' #若勾选，则填入指定值：若不勾选，则填入空值
                }
            }

            if i == 0 and 'Tempo' in original_note['data']:
                new_note['data']['Tempo'] = original_note['data']['Tempo']

            new_notes.append(new_note)

        return new_notes


def main():
    if len(sys.argv) < 2:
        messagebox.showerror("错误", "请通过UTAU插件菜单运行")
        return

    mapper = MappingManager()
    if not mapper.mapping:
        return

    ust_path = sys.argv[-1]
    processor = UstProcessor(ust_path)
    if not processor.sections:
        return

    root = tk.Tk()
    # 设置主窗口图标
    icon_path = os.path.join(PLUGIN_DIR, "icon_64_64.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass  # 如果图标加载失败则忽略
    
    MappingInterface(root, processor.sections, mapper, ust_path)
    root.mainloop()


if __name__ == "__main__":
    main()