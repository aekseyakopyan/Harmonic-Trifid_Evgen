#!/usr/bin/env python3
"""
Утилита для работы с MCP контекстами в разработке.
"""
import os
import sys

# Ensure project root is in path
PROJECT_ROOT = '/Users/set/.gemini/antigravity/playground/Evgeniy'
sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.harmonic_trifid import HarmonicTrifidMCP


def use_context(context_id: str):
    """
    Загружает и отображает контекст для использования в разработке.
    """
    mcp = HarmonicTrifidMCP()
    
    # Получаем метаданные
    metadata = mcp.get_context_metadata(context_id)
    if not metadata:
        print(f"❌ Context @{context_id} not found")
        return
    
    print(f"\n🎯 Using Context @{context_id} - {metadata.name}")
    print("="*60)
    print(f"📁 Path: {metadata.path}")
    print(f"📊 Files: {metadata.files_count}")
    print(f"📝 Description: {metadata.description}")
    print("="*60 + "\n")
    
    # Загружаем файлы
    files = mcp.load_context(context_id)
    
    print(f"✅ Loaded {len(files)} files:\n")
    
    total_lines = 0
    total_size = 0
    
    for file_ctx in files:
        total_lines += file_ctx.lines
        total_size += file_ctx.size
        print(f"  📄 {file_ctx.path}")
        print(f"     Lines: {file_ctx.lines}, Size: {file_ctx.size} bytes")
    
    print(f"\n📈 Total Statistics:")
    print(f"   Total lines: {total_lines:,}")
    print(f"   Total size: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    
    # Получаем структуру
    print(f"\n🏗️  Code Structure:")
    structure = mcp.get_structure(context_id)
    
    total_classes = sum(len(info.get('classes', [])) for info in structure.values() if 'error' not in info)
    total_functions = sum(len(info.get('functions', [])) for info in structure.values() if 'error' not in info)
    
    print(f"   Classes: {total_classes}")
    print(f"   Functions: {total_functions}")
    
    print(f"\n✅ Context @{context_id} ready for use!\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python use_context.py <context_id>")
        print("\nAvailable contexts:")
        print("  @1 - Core Architecture")
        print("  @2 - Parser System")
        print("  @3 - Alexey Personality")
        print("  @4 - Gwen Commander")
        print("  @5 - Dashboard")
        print("  @6 - Applications")
        print("  @7 - Scripts & Utilities")
    else:
        context_id = sys.argv[1].lstrip('@')
        use_context(context_id)
