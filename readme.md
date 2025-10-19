This repo provides a simple NTQQ Sign service implementation.

## Usage

1. Clone the repository;
2. Copy all the file & folder in NTQQ Package (`<package_root>/data/opt/QQ/resources/app`) to the repository folder;
3. Replace `appinfo.json` if needed;
4. Run `build.py`;
5. Run `singer.py` to generate `signer.json`;
6. Fill in the config file `signer.json`;
7. enjoy it!

### Configuration File
`signer.json`:

```json
{
    "host": "127.0.0.1",
    "port": 8080,
    "libs": ["libgnutls.so.30", "./libsymbols.so"],
    "offset": ""
}
```
> NOTE: `offset` WON'T BE PROVIDED BY DEFAULT, you must figure it out by yourself, ~~or delete all the files you've downloaded and shout _"sign fawo"_ in a mysteryous group.~~
