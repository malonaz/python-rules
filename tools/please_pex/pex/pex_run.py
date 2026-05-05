def run(explode=False):
    # Add .bootstrap dir to path, after the initial pex entry
    sys.path.insert(1, os.path.join(sys.path[0], '.bootstrap'))
    if explode or not ZIP_SAFE:
        with explode_zip()():
            for module_dir in MODULE_DIRS:
                add_module_dir_to_sys_path(module_dir, zip_safe=False)
            return main()
    else:
        for module_dir in MODULE_DIRS:
            add_module_dir_to_sys_path(module_dir)
        add_so_import(MODULE_DIRS)
        return main()


if __name__ == '__main__':
    # If PEX_EXPLODE is set, then it should always be exploded.
    explode = os.environ.get('PEX_EXPLODE', '0') != '0'

    # If PEX_INTERPRETER is set, then it starts an interactive console.
    if os.environ.get('PEX_INTERPRETER', '0') != '0':
        import code
        result = code.interact()
    # If PEX_PROFILE_FILENAME is set, then it collects profile information into the filename.
    elif os.environ.get('PEX_PROFILE_FILENAME'):
        with profile(os.environ['PEX_PROFILE_FILENAME'])():
            result = run(explode)
    else:
        result = run(explode)

    sys.exit(result)
