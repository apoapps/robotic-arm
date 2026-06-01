import sys

sys.path.insert(0, "/modules")

try:
    import py_run

    py_run.run_script("robotarm")
    py_run.main_menu()
except Exception as exc:
    print("robotarm boot error:", exc)
    try:
        import py_run

        py_run.main_menu()
    except Exception as menu_exc:
        print("menu error:", menu_exc)
