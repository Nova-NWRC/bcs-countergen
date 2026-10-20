# -*- coding: utf-8 -*-
"""BCS 算子生成器 —— 打包入口（供 PyInstaller 使用）。

双击 exe 即打开图形界面；也支持命令行参数直通：
    BCS算子生成器.exe --cli --spec units.json --out out --pair
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    if "--army" in sys.argv:
        import bcs_army
        argv = [a for a in sys.argv[1:] if a != "--army"]
        raise SystemExit(bcs_army.main(argv))
    if "--cli" in sys.argv:
        import bcs_cli
        argv = [a for a in sys.argv[1:] if a != "--cli"]
        raise SystemExit(bcs_cli.main(argv))
    from bcs_gui import main
    main()
