\# Fingerprint Device Simulator



Simulates fingerprint enrollment and verification without physical hardware.

Enrollment records are stored in memory and lost when the instance is discarded.



\## Usage



```python

from packages.device\_protocol.simulator.mock\_device import MockFingerprintDevice



device = MockFingerprintDevice(device\_id="demo-device")

device.enroll(user\_id="demo-user")



assert device.verify("demo-user", scan\_success=True) is True

assert device.verify("demo-user", scan\_success=False) is False

assert device.verify("unknown-user", scan\_success=True) is False

```



\## Tests



Run from the repository root:



```powershell

python -m pytest tests/unit/test\_mock\_device.py -v

```



\## Limitations



\- No real fingerprints are collected or matched.

\- Scan results are supplied by the caller for simulation.

\- A successful result alone must not grant session or vault access.

\- Finger slots, digital signatures and challenge-response are covered by later tasks.

\- A future hardware adapter will obtain scan results from the device instead of the caller.

