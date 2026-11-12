# Python AdLib/OPL3 library

Wrapper around [Nuked OPL3](https://github.com/nukeykt/Nuked-OPL3).





## Development

```shell
# create venv and install `build` tool
python -m venv env
source env/bin/activate
pip install -U build

# render src/pyopl/_opl3.c with doc-strings from _opl3.pyi file
python tools/add_doc_strings.py
# build the package
python -m build
# install package into venv
pip install --force-reinstall dist/*.whl
# run the unit-tests
python -m unittest discover tests/
```

## Resources

- https://www.asvcorp.ru/darch/docs/sound/opl3/index.html
- https://gist.github.com/alexxior/4ab75ac60bc248634feaf1afba63b129/79ae6d626abcb21578b5df8b93ee4385c50f3131
- https://oplx.com/opl3/docs/ymf262.pdf
- https://www.opl3.com/wp-content/uploads/2019/08/amsc-Programmers-Guide.pdf
- https://forums.submarine.org.uk/phpBB/viewforum.php?f=9