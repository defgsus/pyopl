# Python AdLib/OPL3 library

Wrapper around [Nuked OPL3](https://github.com/nukeykt/Nuked-OPL3).





## Development

```shell
python -m venv env
source env/bin/activate

pip install -U build
python -m build

pip install --force-reinstall dist/*.whl

python -m unittest discover tests/
```

## Resources

- https://www.asvcorp.ru/darch/docs/sound/opl3/index.html
- https://gist.github.com/alexxior/4ab75ac60bc248634feaf1afba63b129/79ae6d626abcb21578b5df8b93ee4385c50f3131
- https://oplx.com/opl3/docs/ymf262.pdf
- https://www.opl3.com/wp-content/uploads/2019/08/amsc-Programmers-Guide.pdf