# -*- coding: utf-8 -*-
import sys
import os
import re
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter import ttk
from tkinter import filedialog
import subprocess

print("loading...")
print("https://b23.tv/QqrzsnF")

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


class ArpabetToPinyinMappingManager:
    def __init__(self):
        self.arpabet_pinyin_path = os.path.join(PLUGIN_DIR, "ARPAbet_to_pinyin.txt")
        self.cmudict_path = os.path.join(PLUGIN_DIR, "cmudict_SPHINX_40.txt")
        self.arpabet_pinyin_mapping = self._load_arpabet_to_pinyin_mapping()
    
    def _load_arpabet_to_pinyin_mapping(self, mapping_path=None):
        if mapping_path:
            self.arpabet_pinyin_path = mapping_path
        mapping = {}
        try:
            with open(self.arpabet_pinyin_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or ';' not in line:
                        continue
                    try:
                        arpabet, pinyin_options = line.split(';', 1)
                        arpabet = arpabet.strip()
                        if not arpabet or not pinyin_options:
                            continue
                        
                        # 解析多个选项，以下划线分隔
                        options = pinyin_options.split('_')
                        formatted_options = []
                        for option in options:
                            # 每个选项可能包含多个音素，以逗号分隔
                            pinyins = option.split(',')
                            formatted_options.append(pinyins)
                        
                        if formatted_options:
                            mapping[arpabet] = formatted_options
                    except Exception:
                        continue
            return mapping if mapping else None
        except Exception as e:
            messagebox.showerror("映射表错误", "加载失败：{0}".format(str(e)))
            return None
    
    def search_word_pronunciations(self, word):
        """
        使用Rust程序搜索单词的发音
        """
        try:
            # 调用Rust程序搜索单词
            executable_path = os.path.join(PLUGIN_DIR, "english_dict_lookup")
            result = subprocess.run([
                executable_path,
                word.upper(),
                self.cmudict_path
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # 解析输出结果
                pronunciations = result.stdout.strip().split('\n')
                pronunciations = [pron.strip() for pron in pronunciations if pron.strip()]
                return pronunciations
            else:
                return []
        except Exception as e:
            print("Error calling Rust program:", e)
            return []


class UstProcessor:
    def __init__(self, ust_path):
        self.ust_path = ust_path
        self.sections = []
        self._parse_ust()

    def _parse_ust(self):
        current_section = None
        try:
            with open(self.ust_path, 'r', encoding='shift_jis', errors='ignore') as f:
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


class EnglishToChineseConverter:
    def __init__(self, master, sections, mapping_manager, ust_path):
        self.master = master
        self.original_sections = sections
        self.mapping_manager = mapping_manager
        self.ust_path = ust_path
        self.modified_sections = []
        self.word_pronunciations = {}  # 存储单词的发音选项
        self.pronunciation_selections = {}  # 存储用户选择的发音
        self.pinyin_selections = {}  # 存储用户选择的拼音
        self.current_pronunciation_combobox = None
        self.current_pinyin_combobox = None
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

        master.title("英文转中文音素工具")
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

        ttk.Button(button_frame, text="选择ARPA表", command=self._select_cmudict_file).pack(side='left', padx=5)
        ttk.Button(button_frame, text="选择拼音表", command=self._select_pinyin_mapping_file).pack(side='left', padx=5)
        ttk.Button(button_frame, text="应用替换", command=self._apply_changes).pack(side='left', padx=5)

        self.mapping_label = ttk.Label(main_frame, text="当前ARPA表：{0}".format(os.path.basename(self.mapping_manager.cmudict_path)))
        self.mapping_label.grid(row=1, column=1, sticky='e', pady=5)
        
        self.pinyin_label = ttk.Label(main_frame, text="当前拼音表：{0}".format(os.path.basename(self.mapping_manager.arpabet_pinyin_path)))
        self.pinyin_label.grid(row=2, column=1, sticky='e', pady=5)

        # Treeview
        self.tree = ttk.Treeview(
            main_frame,
            columns=('lyric', 'arpabet', 'pinyin'),
            show='headings',
            selectmode='none'
        )
        self.tree.heading('lyric', text='原英文')
        self.tree.heading('arpabet', text='ARPAbet方案')
        self.tree.heading('pinyin', text='中文拼音')
        self.tree.column('lyric', width=150, anchor='center')
        self.tree.column('arpabet', width=200, anchor='w')
        self.tree.column('pinyin', width=250, anchor='w')

        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=3, column=0, columnspan=2, sticky='nsew')
        scrollbar.grid(row=3, column=2, sticky='ns')

        main_frame.grid_rowconfigure(3, weight=1)  # 让Treeview可以扩展

        self.tree.bind("<Double-1>", self._on_double_click)

        self._populate_tree()

    def _select_cmudict_file(self):
        file_path = filedialog.askopenfilename(
            title="选择ARPA词典文件",
            filetypes=[("Text files", "*.txt")],
            initialdir=PLUGIN_DIR
        )
        if file_path:
            self.mapping_manager.cmudict_path = file_path
            self.mapping_label.config(text="当前ARPA表：{0}".format(os.path.basename(file_path)))
            # 清除现有选择并重新填充
            self.word_pronunciations.clear()
            self.pronunciation_selections.clear()
            self.pinyin_selections.clear()
            self.tree.delete(*self.tree.get_children())
            self._populate_tree()

    def _select_pinyin_mapping_file(self):
        file_path = filedialog.askopenfilename(
            title="选择ARPAbet到拼音映射表文件",
            filetypes=[("Text files", "*.txt")],
            initialdir=PLUGIN_DIR
        )
        if file_path:
            new_mapping = self.mapping_manager._load_arpabet_to_pinyin_mapping(file_path)
            if new_mapping:
                self.mapping_manager.arpabet_pinyin_mapping = new_mapping
                self.pinyin_label.config(text="当前拼音表：{0}".format(os.path.basename(file_path)))
                # 清除现有选择并重新填充
                self.pinyin_selections.clear()
                self.tree.delete(*self.tree.get_children())
                self._populate_tree()
            else:
                messagebox.showerror("错误", "映射表格式错误")

    def _populate_tree(self):
        for idx, section in enumerate(self.original_sections):
            if section['type'] != 'number':
                self._add_uneditable_row(section)
                continue

            lyric = section['data'].get('Lyric', '')
            # 处理延音符号（加号）
            if lyric == '+':
                self.tree.insert('', 'end', values=(lyric, '自动延音', '自动延音'), tags=('extension', idx))
            else:
                # 获取单词的ARPAbet发音
                pronunciations = self._get_word_pronunciations(lyric)
                if pronunciations:
                    # 默认选择第一个发音
                    default_pronunciation = pronunciations[0]
                    self.word_pronunciations[idx] = pronunciations
                    self.pronunciation_selections[idx] = default_pronunciation
                    
                    # 将ARPAbet转换为拼音选项
                    pinyin_options = self._convert_arpabet_to_pinyin_options(default_pronunciation.split())
                    if pinyin_options:
                        # 默认选择第一个拼音选项
                        default_pinyin = ','.join(pinyin_options[0])
                        self.pinyin_selections[idx] = pinyin_options[0]
                        self.tree.insert('', 'end', values=(lyric, default_pronunciation, default_pinyin), tags=('editable', idx))
                    else:
                        self.tree.insert('', 'end', values=(lyric, default_pronunciation, '无匹配拼音'), tags=('no_pinyin_match', idx))
                else:
                    self.tree.insert('', 'end', values=(lyric, '无匹配发音', '无匹配发音'), tags=('no_match', idx))

        # 配置行的样式
        self.tree.tag_configure('editable', background='#f0f0ff')
        self.tree.tag_configure('extension', background='#f0f0f0', foreground='black')
        self.tree.tag_configure('no_match', foreground='red', background='#f0f0f0')
        self.tree.tag_configure('no_pinyin_match', foreground='orange', background='#f0f0f0')

    def _add_uneditable_row(self, section):
        display_type = {
            'PREV': '前导音符',
            'NEXT': '后续音符',
            'other': '其他'
        }.get(section['type'], '特殊')
        lyric = section['data'].get('Lyric', section['type'])
        self.tree.insert('', 'end', values=(lyric, '（不可修改）', '（不可修改）'), tags=('uneditable',))

    def _get_word_pronunciations(self, word):
        """
        获取单词的发音列表
        """
        if not word or word == '+':
            return []
        
        # 使用Rust程序查找单词发音
        return self.mapping_manager.search_word_pronunciations(word)

    def _convert_arpabet_to_pinyin_options(self, arpabet_phonemes):
        """
        将ARPAbet音素序列转换为拼音选项
        """
        if not self.mapping_manager.arpabet_pinyin_mapping:
            return []
        
        # 对于每个音素，获取其对应的拼音选项
        phoneme_options = []
        for phoneme in arpabet_phonemes:
            if phoneme in self.mapping_manager.arpabet_pinyin_mapping:
                phoneme_options.append(self.mapping_manager.arpabet_pinyin_mapping[phoneme])
            else:
                # 如果没有匹配的拼音，则使用音素本身
                phoneme_options.append([[phoneme]])
        
        # 生成所有可能的组合
        def cartesian_product(sets):
            if not sets:
                return [[]]
            result = []
            for item in sets[0]:
                for rest in cartesian_product(sets[1:]):
                    result.append([item] + rest)
            return result
        
        combinations = cartesian_product(phoneme_options)
        # 将每个组合展平为一维列表
        flattened_combinations = []
        for combination in combinations:
            flattened = []
            for sublist in combination:
                flattened.extend(sublist)
            flattened_combinations.append(flattened)
        
        return flattened_combinations

    def _on_double_click(self, event):
        if self.current_pronunciation_combobox:
            self.current_pronunciation_combobox.destroy()
        if self.current_pinyin_combobox:
            self.current_pinyin_combobox.destroy()

        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id:
            return

        item = self.tree.item(row_id)
        tags = self.tree.item(row_id, 'tags')
        if not tags or 'editable' not in tags:
            return

        # 获取行索引
        idx = int(tags[1])  # 第二个tag是索引

        bbox = self.tree.bbox(row_id, col_id)
        if not bbox:
            return

        if col_id == '#2':  # ARPAbet列
            pronunciations = self.word_pronunciations.get(idx, [])
            if not pronunciations:
                return
            
            self.current_pronunciation_combobox = ttk.Combobox(
                self.tree,
                values=pronunciations,
                state='readonly',
                width=30
            )
            self.current_pronunciation_combobox.set(item['values'][1])
            self.current_pronunciation_combobox.place(
                x=bbox[0],
                y=bbox[1],
                width=bbox[2],
                height=bbox[3]
            )
            self.current_pronunciation_combobox.bind(
                "<<ComboboxSelected>>",
                lambda e, r=row_id, i=idx: self._update_pronunciation_selection(r, i)
            )
        elif col_id == '#3':  # 拼音列
            pronunciation = self.pronunciation_selections.get(idx, "")
            if not pronunciation:
                return
            
            arpabet_phonemes = pronunciation.split()
            pinyin_options = self._convert_arpabet_to_pinyin_options(arpabet_phonemes)
            if not pinyin_options:
                return
            
            # 将选项转换为逗号分隔的字符串
            pinyin_option_strings = [','.join(option) for option in pinyin_options]
            
            self.current_pinyin_combobox = ttk.Combobox(
                self.tree,
                values=pinyin_option_strings,
                state='readonly',
                width=30
            )
            self.current_pinyin_combobox.set(item['values'][2])
            self.current_pinyin_combobox.place(
                x=bbox[0],
                y=bbox[1],
                width=bbox[2],
                height=bbox[3]
            )
            self.current_pinyin_combobox.bind(
                "<<ComboboxSelected>>",
                lambda e, r=row_id, i=idx: self._update_pinyin_selection(r, i)
            )

    def _update_pronunciation_selection(self, row_id, original_idx):
        selected = self.current_pronunciation_combobox.get()
        self.pronunciation_selections[original_idx] = selected
        self.tree.set(row_id, 'arpabet', selected)
        
        # 更新对应的拼音选项
        arpabet_phonemes = selected.split()
        pinyin_options = self._convert_arpabet_to_pinyin_options(arpabet_phonemes)
        if pinyin_options:
            default_pinyin = ','.join(pinyin_options[0])
            self.pinyin_selections[original_idx] = pinyin_options[0]
            self.tree.set(row_id, 'pinyin', default_pinyin)
        else:
            self.tree.set(row_id, 'pinyin', '无匹配拼音')
        
        self.current_pronunciation_combobox.destroy()
        self.current_pronunciation_combobox = None

    def _update_pinyin_selection(self, row_id, original_idx):
        selected = self.current_pinyin_combobox.get()
        # 将选中的拼音字符串转换回列表
        selected_pinyin_list = selected.split(',')
        self.pinyin_selections[original_idx] = selected_pinyin_list
        self.tree.set(row_id, 'pinyin', selected)
        self.current_pinyin_combobox.destroy()
        self.current_pinyin_combobox = None

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

            # 检查是否是延音符号
            lyric = section['data'].get('Lyric', '')
            if lyric == '+':
                # 保留延音符号
                new_sections.append(section)
                continue

            # 检查是否有拼音选择
            if idx not in self.pinyin_selections:
                new_sections.append(section)
                continue

            original_note = section
            pinyin_list = self.pinyin_selections[idx]
            new_notes = self._generate_new_notes(original_note, pinyin_list, overlap_value)
            new_sections.extend(new_notes)
            new_sections.append({
                'header': '[#DELETE]',
                'type': 'number',
                'data': section['data'].copy()
            })

        if UstProcessor(self.ust_path).save(new_sections):
            # 使用自定义完成提示窗口
            CompletionWindow(self.master, "英文转中文音素已完成")
            self.master.destroy()

    def _generate_new_notes(self, original_note, pinyin_list, overlap_value):
        new_notes = []
        total_length = int(original_note['data'].get('Length', 480))
        num_syllables = len(pinyin_list)
        
        if num_syllables == 0:
            return []

        # 平均分配长度给每个音节
        base_length = total_length // num_syllables
        remainder = total_length % num_syllables
        
        for i, pinyin in enumerate(pinyin_list):
            # 分配基础长度，前remainder个音符多分配1个单位长度
            note_length = base_length + (1 if i < remainder else 0)
            if note_length <= 0:
                continue

            new_note = {
                'header': '[#INSERT]',
                'type': 'number',
                'data': {
                    'Lyric': pinyin,
                    'Length': str(note_length),
                    'NoteNum': original_note['data'].get('NoteNum', '60'),
                    'PreUtterance': '0' if self.pre_utterance_var.get() else ' ',
                    'VoiceOverlap': str(overlap_value) if self.overlap_var.get() and i > 0 else ' '
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

    mapper = ArpabetToPinyinMappingManager()
    if not mapper.arpabet_pinyin_mapping:
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
    
    EnglishToChineseConverter(root, processor.sections, mapper, ust_path)
    root.mainloop()


if __name__ == "__main__":
    main()