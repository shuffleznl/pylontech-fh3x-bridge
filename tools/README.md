# Force H3X Modbus Emulator

`h3x_modbus_emulator.py` is a dependency-free Modbus TCP emulator for local Force H3X Bridge validation. It implements the holding-register reads and writes used by the integration and can reproduce the duplicate write response pattern seen in live PyModbus logs.

Run it with Python 3.11 or newer:

```bash
python tools/h3x_modbus_emulator.py --host 0.0.0.0 --port 1502 --duplicate-write-response
```

Then configure Force H3X Bridge to use the emulator host and port `1502`.

Supported function codes:

```text
3   Read holding registers
6   Write single register
16  Write multiple registers
```

The emulator is not a battery simulator. It is a protocol harness for validating register encoding, read/write order, reconnect behavior, and transaction-ID resilience before pushing a HACS release.

Run the PyModbus write-sequence validation locally:

```bash
python -m pip install "pymodbus>=3.11.2"
python tools/validate_modbus_write_sequence.py
```
