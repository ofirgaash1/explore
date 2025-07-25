#!/usr/bin/env python3
"""
Database Debugging Script for ivrit.ai Explore
==============================================

This script helps debug database issues by:
1. Checking database file existence and structure
2. Inspecting tables and their contents
3. Testing transcript file loading
4. Validating index generation process
"""

import sqlite3
import os
import sys
from pathlib import Path
import gzip
import orjson
from typing import List, Optional

def check_database_file(db_path: str) -> bool:
    """Check if database file exists and is valid SQLite."""
    print(f"🔍 Checking database file: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file does not exist: {db_path}")
        return False
    
    file_size = os.path.getsize(db_path)
    print(f"✅ Database file exists, size: {file_size:,} bytes")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check SQLite version
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        print(f"✅ SQLite version: {version}")
        
        # Check if it's a valid SQLite database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ Valid SQLite database, found {len(tables)} tables")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Invalid SQLite database: {e}")
        return False

def inspect_database_structure(db_path: str):
    """Inspect the database structure and tables."""
    print(f"\n📋 Inspecting database structure: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ No tables found in database")
            return
        
        print(f"📊 Found {len(tables)} tables:")
        for table in tables:
            table_name = table[0]
            print(f"  - {table_name}")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"    Columns: {len(columns)}")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                print(f"      {col_name} ({col_type}){' PRIMARY KEY' if pk else ''}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    Rows: {count:,}")
            
            # Show sample data for documents table
            if table_name == "documents" and count > 0:
                cursor.execute(f"SELECT doc_id, source, episode, LENGTH(full_text) as text_length FROM {table_name} LIMIT 5")
                samples = cursor.fetchall()
                print(f"    Sample documents:")
                for doc_id, source, episode, text_length in samples:
                    print(f"      ID: {doc_id}, Source: {source}, Episode: {episode}, Text length: {text_length:,}")
            
            # Show sample data for segments table
            if table_name == "segments" and count > 0:
                cursor.execute(f"SELECT doc_id, segment_id, LENGTH(segment_text) as text_length, start_time, end_time FROM {table_name} LIMIT 5")
                samples = cursor.fetchall()
                print(f"    Sample segments:")
                for doc_id, seg_id, text_length, start, end in samples:
                    print(f"      Doc: {doc_id}, Seg: {seg_id}, Text: {text_length} chars, Time: {start}-{end}s")
            
            print()
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Error inspecting database: {e}")

def check_transcript_files(data_dir: str):
    """Check transcript files in the data directory."""
    print(f"\n📁 Checking transcript files in: {data_dir}")
    
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"❌ Data directory does not exist: {data_dir}")
        return
    
    # Look for full_transcript.json.gz files
    transcript_files = list(data_path.rglob("full_transcript.json.gz"))
    print(f"📄 Found {len(transcript_files)} transcript files")
    
    if not transcript_files:
        print("❌ No transcript files found")
        return
    
    # Check first few files
    for i, file_path in enumerate(transcript_files[:3]):
        print(f"\n  File {i+1}: {file_path}")
        
        try:
            # Check file size
            file_size = file_path.stat().st_size
            print(f"    Size: {file_size:,} bytes")
            
            # Try to read and parse JSON
            with gzip.open(file_path, 'rb') as f:
                data = orjson.loads(f.read())
            
            if isinstance(data, dict) and "segments" in data:
                segments = data["segments"]
                print(f"    Format: Kaldi-style with {len(segments)} segments")
            elif isinstance(data, list):
                print(f"    Format: List with {len(data)} segments")
            else:
                print(f"    Format: Unknown structure")
            
            # Show first segment
            if isinstance(data, dict) and "segments" in data:
                first_seg = data["segments"][0]
            elif isinstance(data, list):
                first_seg = data[0]
            else:
                continue
                
            print(f"    First segment: {first_seg.get('text', 'No text')[:50]}...")
            print(f"    Time: {first_seg.get('start', 'N/A')} - {first_seg.get('end', 'N/A')}")
            
        except Exception as e:
            print(f"    ❌ Error reading file: {e}")

def test_index_generation(data_dir: str, output_db: str):
    """Test the index generation process."""
    print(f"\n🔧 Testing index generation")
    print(f"  Data directory: {data_dir}")
    print(f"  Output database: {output_db}")
    
    try:
        # Import the necessary modules
        sys.path.append('.')
        from app.utils import get_transcripts
        from app.services.index import IndexManager
        
        print("✅ Successfully imported modules")
        
        # Get transcript records
        print("📋 Getting transcript records...")
        file_records = get_transcripts(Path(data_dir))
        file_records = file_records[:5] #DEBUG
        print(f"✅ Found {len(file_records)} transcript records")
        
        if not file_records:
            print("❌ No transcript records found")
            return
        
        # Show first few records
        for i, record in enumerate(file_records[:3]):
            print(f"  Record {i+1}: {record.id}")
            print(f"    Path: {record.json_path}")
        
        # Test index generation
        print("\n🔨 Building index...")
        index_mgr = IndexManager(
            file_records=file_records,
            db_type="sqlite",
            path=output_db
        )
        
        print("✅ Index built successfully")
        
        # Get index statistics
        index = index_mgr.get()
        doc_count, total_chars = index.get_document_stats()
        print(f"📊 Index statistics:")
        print(f"  Documents: {doc_count}")
        print(f"  Total characters: {total_chars:,}")
        
        # Test a simple search
        print("\n🔍 Testing search functionality...")
        try:
            # Get first document text
            first_text = index.get_document_text(0)
            if first_text:
                # Search for first few words
                search_words = first_text.split()[:3]
                if search_words:
                    search_query = " ".join(search_words)
                    print(f"  Searching for: '{search_query}'")
                    hits = index.search_hits(search_query)
                    print(f"  Found {len(hits)} hits")
            else:
                print("  No text found in first document")
        except Exception as e:
            print(f"  ❌ Search test failed: {e}")
        
        # Print first 3 records of each table
        print("\n📑 Printing first 3 records of each table:")
        try:
            conn = sqlite3.connect(output_db)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                print(f"\nTable: {table}")
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in cursor.fetchall()]
                cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                rows = cursor.fetchall()
                if not rows:
                    print("  (No records)")
                else:
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        print(f"  {row_dict}")
            conn.close()
        except Exception as e:
            print(f"❌ Error printing table samples: {e}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this script from the project root directory")
    except Exception as e:
        print(f"❌ Error during index generation: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main debugging function."""
    print("🐛 ivrit.ai Explore Database Debugger")
    print("=" * 50)
    
    # Configuration
    data_dir = r"C:\Users\Yanir\ivrit-dataset\audio-v2-transcripts"
    db_path = r"C:\Users\Yanir\ivrit-dataset\explore-index.db"
    
    print(f"Configuration:")
    print(f"  Data directory: {data_dir}")
    print(f"  Database path: {db_path}")
    print()
    
    # Check database file
    db_exists = check_database_file(db_path)
    
    if db_exists:
        # Inspect existing database
        inspect_database_structure(db_path)
    else:
        print("\n📝 No existing database found, will test index generation")
    
    # Check transcript files
    check_transcript_files(data_dir)
    
    # Test index generation
    test_index_generation(data_dir, db_path)
    
    print("\n✅ Debugging complete!")

if __name__ == "__main__":
    main()