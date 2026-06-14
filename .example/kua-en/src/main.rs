use std::collections::HashMap;
use std::env;
use std::fs::File;
use std::io::{BufRead, BufReader, Write, stdin, stdout};

fn get_base_word(s: &str) -> String {
    if let Some(pos) = s.find('(') {
        s[..pos].trim().to_string()
    } else {
        s.trim().to_string()
    }
    .to_uppercase()
}

fn load_dictionary_from_text(file_path: &str) -> Result<HashMap<String, Vec<String>>, Box<dyn std::error::Error>> {
    let file = File::open(file_path)?;
    let reader = BufReader::new(file);
    let mut dict = HashMap::new();

    for line in reader.lines() {
        let line = line?;
        let line = line.trim();
        if line.is_empty() || line.starts_with("#") {
            continue;
        }

        // Skip lines that start with non-alphabetic characters (like punctuation marks)
        if let Some(first_char) = line.chars().next() {
            if !first_char.is_alphabetic() {
                continue;
            }
        }

        if let Some((w, pron)) = line.split_once(char::is_whitespace) {
            let base_word = get_base_word(w);
            let pron = pron.trim().to_string();
            dict.entry(base_word)
                .or_insert_with(Vec::new)
                .push(pron);
        }
    }
    
    Ok(dict)
}

fn interactive_search(dict: &HashMap<String, Vec<String>>) {
    loop {
        let mut input = String::new();
        if stdin().read_line(&mut input).is_err() {
            break;
        }
        
        let word = input.trim();
        
        if word.eq_ignore_ascii_case("exit") || word.eq_ignore_ascii_case("quit") {
            break;
        }
        
        if word.is_empty() {
            continue;
        }
        
        let base_word = get_base_word(word);
        if let Some(prons) = dict.get(&base_word) {
            for pron in prons {
                println!("{}", pron);
            }
        }
        // 未找到单词时不输出任何信息
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    
    // 至少需要一个参数（字典文件路径）
    if args.len() < 2 {
        eprintln!("Usage: {} <word> <dictionary_file>", args[0]);
        std::process::exit(1);
    }

    let word = &args[1];
    let file_path = if args.len() > 2 { &args[2] } else { "cmudict_SPHINX_40.txt" };

    // 加载字典
    let dict = match load_dictionary_from_text(file_path) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("Error loading dictionary: {}", e);
            std::process::exit(1);
        }
    };

    // 查询单词
    let base_word = get_base_word(word);
    match dict.get(&base_word) {
        Some(prons) => {
            for pron in prons {
                println!("{}", pron);
            }
        }
        None => {
            // 未找到单词时静默退出，不输出任何信息
            std::process::exit(1);
        }
    }
}