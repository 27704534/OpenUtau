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

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


class MappingManager:
    def __init__(self):
        self.mapping_path = os.path.join(PLUGIN_DIR, "pinyin.txt")
        self.mapping = self._load_mapping()

    def _load_mapping(self, mapping_path=None):
        if mapping_path:
            self.mapping_path = mapping_path
        mapping = {}
        try:
            with open(self.mapping_path, 'r', encoding='utf-8') as f:
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
                    'PreUtterance': '0' if self.pre_utterance_var.get() else '',
                    'VoiceOverlap': str(overlap_value) if self.overlap_var.get() and i > 0 else '0'
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