## Standard Service Routines
The following service routines are a part of the standard pyGestalt _gestaltVirtualNodes_ class, and are necessary for supporting essential node behavior. These include associating virtual and physical nodes on the Gestalt network, syncronizing commands across nodes, and for loading new firmware.

| Port | Service Routine                             |
|------|---------------------------------------------|
| 1    | [_statusRequest_](#statusrequest)           |
|------|---------------------------------------------|
| 2    | [_bootCommandRequest_](#bootcommandrequest) |
|------|---------------------------------------------|
| 3    | [_bootWriteRequest_](#bootwriterequest)     |
|------|---------------------------------------------|
| 4    | [_bootReadRequest_](#bootreadrequest)       |
|------|---------------------------------------------|
| 5    | [_urlRequest_](#urlrequest)                 |
|------|---------------------------------------------|
| 6    | [_setAddressRequest_](#setaddressrequest)   |
|------|---------------------------------------------|
| 7    | [_identifyRequest_](#identifyrequest)       |
|------|---------------------------------------------|
| 8    | [_syncRequest_](#syncrequest)               |
|------|---------------------------------------------|
| 255  | [_resetRequest_](#resetrequest)             |
|------|---------------------------------------------|

### _statusRequest_

- Port Number: 1
- Standard Mode: Unicast
- Physical Node Function: _svcStatus()_

#### Outbound (Virtual -> Physical Node) Payload Format: _Empty_

#### Inbound (Physical -> Virtual Node) Payload Format:

| Payload Byte | Description                                  |
|--------------|----------------------------------------------|
| Byte 0       | Status  _("b" = bootloader, "a" = application)_|
|--------------|----------------------------------------------|
| Byte 1       | Application Validity  _(170 if valid)_         |
|--------------|----------------------------------------------|

- _Status_: Reports whether the physical node is running the bootloader or the application firmware.
- _Application Validity_: Reports if the application firmware loaded onto the node is valid, by returning the value of the "application valid" EEPROM flag. At the beginning of the bootloading process, an EEPROM flag is cleared. If the bootloader completes successfully, this flag is then set to 170.

### _bootCommandRequest_

- Port Number: 2
- Standard Mode: Unicast
- Physical Node Function: _svcBootloaderCommand()_
- Not avaliable on Arduino-based nodes.

#### Outbound (Virtual -> Physical Node) Payload Format:

| Payload Byte | Description                                           |
|--------------|-------------------------------------------------------|
| Byte 0       | Command  _(0 = start bootloader, 1 = start application)_|
|--------------|-------------------------------------------------------|

- _Command_: Starts the bootloader or starts the application.


#### Inbound (Physical -> Virtual Node) Payload Format:

| Payload Byte | Description                                         |
|--------------|-----------------------------------------------------|
| Byte 0       | Response  _(5 = bootloader started, 9 = app. started)_|
|--------------|----------------------------------------------|
| Byte 1       | Page Number _(Byte 0)_            |
|--------------|----------------------------------------------|
| Byte 2       | Page  Number _(Byte 1)_         |
|--------------|----------------------------------------------|

- _Response_: Indicates that either the bootloader or the application has been started
- _Page Number_: Has no meaning in the context of the bootloader command.

### _bootWriteRequest_
- Port Number: 3
- Standard Mode: Unicast
- Physical Node Function: _svcBootloaderData()_
- Not avaliable on Arduino-based nodes.

#### Outbound (Virtual -> Physical Node) Payload Format:

| Payload Byte | Description                  |
|--------------|------------------------------|
| Byte 0       | Command  _(2 = write page)_  |
|--------------|------------------------------|
| Byte 1       | Page Number _(Byte 0)_       |
|--------------|------------------------------|
| Byte 2       | Page Number _(Byte 1)_       |
|--------------|------------------------------|
| Byte 3 -> N  | Page Data                    |
|--------------|------------------------------|

- _Command_: This byte must be equal to 2 for the write command to be accepted.
- _Page Number_: The starting memory address of the page to be written
- _Page Data_: The contents of the memory page to be written

#### Inbound (Physical -> Virtual Node) Payload Format:

| Payload Byte | Description                  |
|--------------|------------------------------|
| Byte 0       | Response  _(1 = writing page now)_  |
|--------------|------------------------------|
| Byte 1       | Page Number _(Byte 0)_       |
|--------------|------------------------------|
| Byte 2       | Page Number _(Byte 1)_       |
|--------------|------------------------------|

- _Response_: This byte will equal 1 if the bootloader has successfully begun to write the memory page.
- _Page Number_: The starting memory address of the page currently being written

### _bootReadRequest_
- Port Number: 4
- Standard Mode: Unicast
- Physical Node Function: _svcBootloaderReadPage()_
- Not avaliable on Arduino-based nodes.

#### Outbound (Virtual -> Physical Node) Payload Format:

| Payload Byte | Description                  |
|--------------|------------------------------|
| Byte 0       | Page Number  _(Byte 0)_      |
|--------------|------------------------------|
| Byte 1       | Page Number _(Byte 1)_       |
|--------------|------------------------------|

- _Page Number_: The starting memory address of the requested page

#### Inbound (Physical -> Virtual Node) Payload Format:

| Payload Byte | Description                  |
|--------------|------------------------------|
| Byte 0       | Page Number  _(Byte 0)_      |
|--------------|------------------------------|
| Byte 1       | Page Number _(Byte 1)_       |
|--------------|------------------------------|
| Byte 2 -> N  | Page Data                    |
|--------------|------------------------------|

- _Page Number_: The starting memory address of the returned page data
- _Page Data_: The contents of the requested memory page

### _urlRequest_
- Port Number: 5
- Standard Mode: Unicast
- Physical Node Function: _svcRequestURL()_

#### Outbound (Virtual -> Physical Node) Payload Format: _Empty_

#### Inbound (Physical -> Virtual Node) Payload Format:

| Payload Byte | Description                  |
|--------------|------------------------------|
| Byte 0 -> N  | Virtual Node URL             |
|--------------|------------------------------|

- _Virtual Node URL_: An ASCII-encoded URL pointing to the location of the virtual node python file. This makes it possible for virtual node files to be automatically downloaded from a location of the node creator's choosing.

### _setAddressRequest_
- Port Number: 6
- Standard Mode: Multicast
- Physical Node Function: _svcSetIPAddress()_

#### Outbound (Virtual -> Physical Node) Payload Format:

| Payload Byte | Description                  |
|--------------|------------------------------|
| Byte 0       | New Address  _(Byte 0)_      |
|--------------|------------------------------|
| Byte 1       | New Address  _(Byte 1)_      |
|--------------|------------------------------|

- _New Address_: The new address that the identified node should assign to itself

#### Inbound (Physical -> Virtual Node) Payload Format:

| Payload Byte | Description                  |
|--------------|------------------------------|
| Byte 0 -> N  | Virtual Node URL             |
|--------------|------------------------------|

- _Virtual Node URL_: An ASCII-encoded URL pointing to the location of the virtual node python file. This makes it possible for virtual node files to be automatically downloaded from a location of the node creator's choosing.

### _identifyRequest_
- Port Number: 7
- Standard Mode: Unicast
- Physical Node Function: _svcIdentifyNode()_
- No response expected.

#### Outbound (Virtual -> Physical Node) Payload Format: _Empty_
#### Inbound (Physical -> Virtual Node) Packet: _None_

### _syncRequest_
- Port Number: 8
- Standard Mode: Multicast
- Physical Node Function: __
- No response expected.

#### Outbound (Virtual -> Physical Node) Payload Format: _Empty_
#### Inbound (Physical -> Virtual Node) Packet: _None_

### _resetRequest_
- Port Number: 255
- Standard Mode: Unicast
- Physical Node Function: _svcResetNode()_
- No response expected.

#### Outbound (Virtual -> Physical Node) Payload Format: _Empty_
#### Inbound (Physical -> Virtual Node) Packet: _None_