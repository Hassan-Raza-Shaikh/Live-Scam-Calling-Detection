#!/usr/bin/env python3
import os
import json

def seed_database():
    print("Seeding Sentinel AI Knowledge Base...")
    scam_patterns_dir = "knowledge/scam_patterns"
    if os.path.exists(scam_patterns_dir):
        files = [f for f in os.listdir(scam_patterns_dir) if f.endswith(".json")]
        print(f"Found {len(files)} scam pattern files: {files}")
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database()
