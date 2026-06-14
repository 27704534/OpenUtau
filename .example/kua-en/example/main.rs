use std::collections::HashMap;
use std::env;
use std::fs::File;
use std::io::{BufRead, BufReader, Write, stdin, stdout};
use std::path::Path;

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
        if line.is_empty() {
            continue;
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

fn save_dictionary_to_cache(dict: &HashMap<String, Vec<String>>, cache_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let mut file = File::create(cache_path)?;
    let serialized = bincode::serialize(dict)?;
    file.write_all(&serialized)?;
    Ok(())
}

fn load_dictionary_from_cache(cache_path: &str) -> Result<HashMap<String, Vec<String>>, Box<dyn std::error::Error>> {
    let file = File::open(cache_path)?;
    let reader = BufReader::new(file);
    let dict = bincode::deserialize_from(reader)?;
    Ok(dict)
}

fn load_dictionary(file_path: &str) -> Result<HashMap<String, Vec<String>>, Box<dyn std::error::Error>> {
    let cache_path = format!("{}.tmp", file_path);
    
    // 检查缓存文件是否存在且比原文件更新
    if Path::new(&cache_path).exists() {
        if let (Ok(metadata_cache), Ok(metadata_original)) = (
            std::fs::metadata(&cache_path),
            std::fs::metadata(file_path)
        ) {
            if let (Ok(modified_cache), Ok(modified_original)) = (
                metadata_cache.modified(),
                metadata_original.modified()
            ) {
                if modified_cache >= modified_original {
                    return load_dictionary_from_cache(&cache_path);
                }
            }
        }
    }
    
    // 从原文件加载并创建缓存
    let dict = load_dictionary_from_text(file_path)?;
    
    // 静默保存缓存，忽略错误
    let _ = save_dictionary_to_cache(&dict, &cache_path);
    
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

fn print_help(program_name: &str) {
    println!("Usage: {} [OPTIONS] [WORD] [FILE]", program_name);
    println!();
    println!("Search for word pronunciations in a dictionary file.");
    println!();
    println!("Arguments:");
    println!("  WORD                    Word to search for");
    println!("  FILE                    Dictionary file path (default: cmudict_SPHINX_40.txt)");
    println!();
    println!("Options:");
    println!("  -i, --interactive       Enable interactive mode");
    println!("  -h, --help              Print this help message");
    println!();
    println!("Examples:");
    println!("  {} hello                    # Search for 'hello'", program_name);
    println!("  {} hello dictionary.txt     # Search with custom dictionary", program_name);
    println!("  {} -i dictionary.txt        # Interactive mode", program_name);
    println!("  {} --interactive            # Interactive mode with default dictionary", program_name);
    println!();
    println!("Interactive mode:");
    println!("  - Enter words one per line to get pronunciations");
    println!("  - Type 'exit' or 'quit' to exit");
    println!("  - No prompt is displayed for cleaner output");
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let program_name = args[0].clone();
    
    // 解析参数
    let mut word = None;
    let mut file_path = "cmudict_SPHINX_40.txt".to_string();
    let mut interactive_mode = false;
    
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "-h" | "--help" => {
                print_help(&program_name);
                return;
            }
            "-i" | "--interactive" => {
                interactive_mode = true;
            }
            arg => {
                if word.is_none() && !arg.starts_with('-') {
                    word = Some(arg.to_string());
                } else if !arg.starts_with('-') {
                    file_path = arg.to_string();
                } else {
                    eprintln!("Unknown option: {}", arg);
                    std::process::exit(1);
                }
            }
        }
        i += 1;
    }

    // 加载字典
    let dict = match load_dictionary(&file_path) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("Error loading dictionary: {}", e);
            std::process::exit(1);
        }
    };

    if interactive_mode {
        interactive_search(&dict);
    } else {
        // 单次查询模式
        match word {
            Some(w) => {
                let base_word = get_base_word(&w);
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
            None => {
                eprintln!("Error: WORD argument required in non-interactive mode");
                eprintln!("Use '{} --help' for usage information", program_name);
                std::process::exit(1);
            }
        }
    }
}