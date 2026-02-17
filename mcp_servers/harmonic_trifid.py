#!/usr/bin/env python3
"""
MCP Server для проекта Harmonic Trifid.
Предоставляет структурированный доступ к базе знаний проекта.
"""
import os
import json
import ast
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


PROJECT_ROOT = Path(os.getenv('PROJECT_ROOT', '/Users/set/.gemini/antigravity/playground/Evgeniy'))


@dataclass
class ContextMetadata:
    """Метаданные контекста."""
    context_id: str
    name: str
    path: str
    files_count: int
    last_modified: str
    description: str


@dataclass
class FileContext:
    """Контекст файла."""
    path: str
    content: str
    language: str
    size: int
    lines: int


class HarmonicTrifidMCP:
    """MCP сервер для Harmonic Trifid."""
    
    CONTEXTS = {
        "1": {
            "name": "Core Architecture",
            "path": "core/",
            "description": "Базовая архитектура: AI engine, config, utils, database"
        },
        "2": {
            "name": "Parser System",
            "path": "systems/parser/",
            "description": "7-уровневый конвейер фильтрации лидов, ML классификатор"
        },
        "3": {
            "name": "Alexey Personality",
            "path": "systems/alexey/",
            "description": "Личность менеджера Алексея, RAG, диалоги"
        },
        "4": {
            "name": "Gwen Commander",
            "path": "systems/gwen/",
            "description": "Командный центр управления через Telegram"
        },
        "5": {
            "name": "Dashboard",
            "path": "systems/dashboard/",
            "description": "FastAPI веб-панель управления и аналитика"
        },
        "6": {
            "name": "Applications",
            "path": "apps/",
            "description": "Основные приложения: парсеры, мониторинг"
        },
        "7": {
            "name": "Scripts & Utilities",
            "path": "scripts/",
            "description": "Утилиты, миграции, тестирование"
        }
    }
    
    def __init__(self):
        """Инициализация MCP сервера."""
        self.project_root = PROJECT_ROOT
        self.cache: Dict[str, List[FileContext]] = {}
    
    def get_context_metadata(self, context_id: str) -> Optional[ContextMetadata]:
        """Получает метаданные контекста."""
        if context_id not in self.CONTEXTS:
            return None
        
        ctx = self.CONTEXTS[context_id]
        ctx_path = self.project_root / ctx['path']
        
        if not ctx_path.exists():
            return None
        
        # Подсчитываем файлы
        python_files = list(ctx_path.rglob('*.py'))
        files_count = len(python_files)
        
        # Находим последнюю модификацию
        if python_files:
            last_modified = max(f.stat().st_mtime for f in python_files)
            from datetime import datetime
            last_modified_str = datetime.fromtimestamp(last_modified).isoformat()
        else:
            last_modified_str = "N/A"
        
        return ContextMetadata(
            context_id=context_id,
            name=ctx['name'],
            path=ctx['path'],
            files_count=files_count,
            last_modified=last_modified_str,
            description=ctx['description']
        )
    
    def load_context(self, context_id: str, use_cache: bool = True) -> List[FileContext]:
        """
        Загружает все файлы из контекста.
        """
        if use_cache and context_id in self.cache:
            return self.cache[context_id]
        
        if context_id not in self.CONTEXTS:
            return []
        
        ctx = self.CONTEXTS[context_id]
        ctx_path = self.project_root / ctx['path']
        
        if not ctx_path.exists():
            return []
        
        file_contexts = []
        
        # Загружаем все Python файлы
        for py_file in ctx_path.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                rel_path = py_file.relative_to(self.project_root)
                lines = content.count('\n') + 1
                size = py_file.stat().st_size
                
                file_contexts.append(FileContext(
                    path=str(rel_path),
                    content=content,
                    language='python',
                    size=size,
                    lines=lines
                ))
            except Exception as e:
                print(f"Error loading {py_file}: {e}")
                continue
        
        # Кэшируем результат
        self.cache[context_id] = file_contexts
        
        return file_contexts
    
    def search_in_context(
        self,
        context_id: str,
        query: str,
        case_sensitive: bool = False
    ) -> List[Dict]:
        """
        Поиск по содержимому файлов в контексте.
        """
        files = self.load_context(context_id)
        results = []
        
        search_query = query if case_sensitive else query.lower()
        
        for file_ctx in files:
            content = file_ctx.content if case_sensitive else file_ctx.content.lower()
            
            if search_query in content:
                lines = file_ctx.content.split('\n')
                matches = []
                
                for i, line in enumerate(lines, 1):
                    check_line = line if case_sensitive else line.lower()
                    if search_query in check_line:
                        context_start = max(0, i - 3)
                        context_end = min(len(lines), i + 2)
                        context_lines = lines[context_start:context_end]
                        
                        matches.append({
                            'line_number': i,
                            'line': line.strip(),
                            'context': '\n'.join(context_lines)
                        })
                
                if matches:
                    results.append({
                        'file': file_ctx.path,
                        'matches': matches
                    })
        
        return results
    
    def get_structure(self, context_id: str) -> Dict:
        """Получает структуру файлов и классов в контексте."""
        files = self.load_context(context_id)
        structure = {}
        
        for file_ctx in files:
            try:
                tree = ast.parse(file_ctx.content)
                
                classes = []
                functions = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = [
                            m.name for m in node.body 
                            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ]
                        classes.append({
                            'name': node.name,
                            'methods': methods,
                            'line': node.lineno
                        })
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not any(node.lineno >= c['line'] for c in classes):
                            functions.append({
                                'name': node.name,
                                'line': node.lineno
                            })
                
                structure[file_ctx.path] = {
                    'classes': classes,
                    'functions': functions,
                    'lines': file_ctx.lines
                }
            except Exception:
                structure[file_ctx.path] = {'error': 'Failed to parse'}
        
        return structure
    
    def export_context(self, context_id: str, output_path: str) -> bool:
        """Экспортирует контекст в JSON файл."""
        files = self.load_context(context_id)
        metadata = self.get_context_metadata(context_id)
        
        export_data = {
            'metadata': asdict(metadata) if metadata else None,
            'files': [asdict(f) for f in files]
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python harmonic_trifid.py <command> [args]")
        print("\nCommands:")
        print("  list                    - Список всех контекстов")
        print("  info <context_id>       - Информация о контексте")
        print("  load <context_id>       - Загрузить контекст")
        print("  search <context_id> <query> - Поиск в контексте")
        print("  structure <context_id>  - Структура кода в контексте")
        print("  export <context_id> <path> - Экспорт контекста")
        return
    
    mcp = HarmonicTrifidMCP()
    command = sys.argv[1]
    
    if command == 'list':
        print("\n📚 Доступные контексты:\n")
        for ctx_id, ctx_info in mcp.CONTEXTS.items():
            print(f"  @{ctx_id} - {ctx_info['name']}")
            print(f"      {ctx_info['description']}")
            print(f"      Path: {ctx_info['path']}\n")
    
    elif command == 'info' and len(sys.argv) >= 3:
        context_id = sys.argv[2].lstrip('@')
        metadata = mcp.get_context_metadata(context_id)
        
        if metadata:
            print(f"\n📊 Context @{metadata.context_id} - {metadata.name}\n")
            print(f"  Path: {metadata.path}")
            print(f"  Files: {metadata.files_count}")
            print(f"  Last modified: {metadata.last_modified}")
            print(f"  Description: {metadata.description}\n")
        else:
            print(f"❌ Context @{context_id} not found")
    
    elif command == 'load' and len(sys.argv) >= 3:
        context_id = sys.argv[2].lstrip('@')
        files = mcp.load_context(context_id)
        
        print(f"\n✅ Loaded {len(files)} files from context @{context_id}\n")
        for file_ctx in files[:10]:
            print(f"  📄 {file_ctx.path} ({file_ctx.lines} lines)")
        
        if len(files) > 10:
            print(f"  ... и еще {len(files) - 10} файлов")
    
    elif command == 'search' and len(sys.argv) >= 4:
        context_id = sys.argv[2].lstrip('@')
        query = ' '.join(sys.argv[3:])
        
        results = mcp.search_in_context(context_id, query)
        
        print(f"\n🔍 Поиск '{query}' в context @{context_id}\n")
        print(f"Найдено совпадений в {len(results)} файлах:\n")
        
        for result in results[:5]:
            print(f"📄 {result['file']}")
            for match in result['matches'][:3]:
                print(f"   Строка {match['line_number']}: {match['line']}")
            print()
    
    elif command == 'structure' and len(sys.argv) >= 3:
        context_id = sys.argv[2].lstrip('@')
        structure = mcp.get_structure(context_id)
        
        print(f"\n🏗️  Структура context @{context_id}\n")
        
        for file_path, info in list(structure.items())[:5]:
            print(f"📄 {file_path}")
            if 'error' in info:
                print(f"   ⚠️  {info['error']}")
            else:
                if info['classes']:
                    print(f"   Classes: {', '.join(c['name'] for c in info['classes'])}")
                if info['functions']:
                    print(f"   Functions: {', '.join(f['name'] for f in info['functions'])}")
            print()
    
    elif command == 'export' and len(sys.argv) >= 4:
        context_id = sys.argv[2].lstrip('@')
        output_path = sys.argv[3]
        
        if mcp.export_context(context_id, output_path):
            print(f"✅ Context @{context_id} exported to {output_path}")
        else:
            print(f"❌ Export failed")
    
    else:
        print("❌ Unknown command or missing arguments")


if __name__ == "__main__":
    main()
