__version__ = "7.46"
import json
import re
import os
import logging

class VersionChecker:
    def __init__(self):
        self.expected_version = None
        
    def get_python_version(self, python_file_path):
        """Extract version from Python file"""
        try:
            with open(python_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for __version__ = "x.xx?" pattern
            version_pattern = r'__version__\s*=\s*["\']([\d.]+[a-zA-Z]?)["\']'
            match = re.search(version_pattern, content)
            if match:
                return match.group(1).strip()
        except Exception as e:
            print(f"Error reading Python file: {e}")
        return None
        
    def get_bash_version(self, bash_file_path):
        """Extract version from Bash script"""
        try:
            with open(bash_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for __version__ = "x.xx" pattern
            version_pattern = r'__version__\s*=\s*["\']([\d.]+)["\']'
            match = re.search(version_pattern, content)
            if match:
                return match.group(1).strip()
        except Exception as e:
            print(f"Error reading Bash file: {e}")
        return None

    def get_html_version(self, html_file_path):
        """Extract version from HTML file"""
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for meta tag or comment pattern
            meta_pattern = r'<meta\s+name=["\']version["\']\s+content=["\']([\d.]+)["\']'
            comment_pattern = r'<!--\s*version:\s*([\d.]+)\s*-->'
            
            match = re.search(meta_pattern, content) or re.search(comment_pattern, content)
            if match:
                return match.group(1).strip()
        except Exception as e:
            print(f"Error reading HTML file: {e}")
        return None
    
    def get_json_version(self, json_file_path):
        """Extract version from JSON config file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return config.get('VERSION', '').strip()
        except Exception as e:
            print(f"Error reading JSON file: {e}")
        return None
    
    def check_versions(self, python_files, bash_files, html_files, json_files):
        versions = {}
        
        # Collect versions from all files
        for py_file in python_files:
            if os.path.exists(py_file):
                versions[py_file] = self.get_python_version(py_file)

        for sh_file in bash_files:
            if os.path.exists(sh_file):
                versions[sh_file] = self.get_bash_version(py_file)        
        
        for html_file in html_files:
            if os.path.exists(html_file):
                versions[html_file] = self.get_html_version(html_file)
        
        for json_file in json_files:
            if os.path.exists(json_file):
                versions[json_file] = self.get_json_version(json_file)
        
        # Find the most common version (expected version)
        version_counts = {}
        for version in versions.values():
            if version:
                version_counts[version] = version_counts.get(version, 0) + 1
        
        if version_counts:
            self.expected_version = max(version_counts.items(), key=lambda x: x[1])[0]
        
        # Check for inconsistencies
        inconsistencies = []
        for file_path, version in versions.items():
                inconsistencies.append((file_path, version))
        
        return inconsistencies
    

if __name__ == "__main__":
    checker = VersionChecker()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    # Define file paths
    python_files = ['wk.py', 'version.py', 'web_routes.py']
    bash_files = ['install.sh']
    html_files = ['templates_plugin/index.html']
    json_files = ['config_gen.json', 'config_loc.json', '/home/pi/.workclock/config_loc.json']
    
    # Check versions
    inconsistencies = checker.check_versions(python_files, bash_files, html_files, json_files)
    
    print("Versions in this build:")
    for file_path, version in inconsistencies:
        print(f"  {file_path}: {version}")
        






