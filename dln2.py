import usb.core
import usb.util
import time


def debug_print(string):
    #print(string)
    return


def time_ms():
    return round(time.time() * 1000)


class Dlndev():
    USB_VID = 0x1d50
    USB_PID = 0x6170

    MODULE_IRQ = 0x0f

    def __init__(self, usbdev):
        self.usbdev = usbdev
        self.gpiolist = {}  # used for irq handling

    def addgpio(self, num, gpio):
        self.gpiolist[num] = gpio

    def _irqwait(self, timeout_ms=1000):
        starttime = time_ms()
        while 43:
            ret = self.usbdev.read(0x89, 280, starttime + timeout_ms - time_ms())
            debug_print(f'ret: {ret}')
            if ret[0] == 14 and ret[2] == self.MODULE_IRQ:
                gpnum = ret[11]
                gpval = ret[13]
                gpio = self.gpiolist.get(gpnum)
                if gpio:
                    gpio.irqcallback(gpnum, gpval)
            else:
                break
        return ret

    def irqwait(self, timeout_ms=1000):
        try:
            self._irqwait(timeout_ms)
        except usb.core.USBTimeoutError:
            return None
        return 0

    def _trans(self, buffer, raw=True):
        self.usbdev.write(9, buffer)

        debug_print(f'send: {buffer}')
        ret = self._irqwait()
        if raw == "real":
            return ret
        if raw:
            return ret[12:]

        # if not raw do the answer as integer
        if len(ret) == 12:
            return int.from_bytes(ret[10:], byteorder='little', signed=False)
        if len(ret) == 14:
            return int.from_bytes(ret[10:], byteorder='little', signed=False)
        if len(ret) == 13:
            return ret[12]
        if len(ret) > 14:
            return ret[12:]
        if len(ret) == 11:
            return ret[10]
        return ret


class Dln():
    MODULE_GENERIC = 0x00
    MODULE_GPIO = 0x01
    MODULE_SPI = 0x02
    MODULE_I2C = 0x03
    MODULE_ADC = 0x06
    MODULE_UART = 0x0e
    HANDLE_EVENT = 0
    HANDLE_CTRL = 1
    HANDLE_GPIO = 2
    HANDLE_I2C = 3
    HANDLE_SPI = 4
    HANDLE_ADC = 5

    def __init__(self, dev, module, handle):
        self.dev = dev.usbdev
        self.dln = dev

        print(type(self.dev))
        self.module = module
        self.handle = handle

    def _tx(self, cmd, data=bytearray([]), raw=True):
        buffer = bytearray([8 + len(data), 0, cmd, self.module, 0, 0, self.handle, 0])
        buffer = buffer + data
        return self.dln._trans(buffer, raw=raw)

    def irqwait(self, timeout_ms):
        return self.dln.irqwait(timeout_ms)

    def _txi(self, cmd, data=bytearray([])):  #tx but interprete the answer (raw=false)
        return self._tx(cmd, data, raw=False)


class Dln2SpiInterface(Dln):
    ENABLE                         = 0x11
    DISABLE                        = 0x12
    SET_MODE                       = 0x14
    SET_FRAME_SIZE                 = 0x16
    SET_FREQUENCY                  = 0x18
    READ_WRITE                     = 0x1A
    READ                           = 0x1B
    WRITE                          = 0x1C
    SET_SS                         = 0x26
    SS_MULTI_ENABLE                = 0x38
    SS_MULTI_DISABLE               = 0x39
    GET_SUPPORTED_FRAME_SIZES      = 0x43
    GET_SS_COUNT                   = 0x44
    GET_MIN_FREQUENCY              = 0x45
    GET_MAX_FREQUENCY              = 0x46

    def __init__(self, dev, freq="min"):
        Dln.__init__(self, dev, module=Dln.MODULE_SPI, handle=Dln.HANDLE_SPI)
        print(self._tx(Dln2SpiInterface.ENABLE, bytearray([0]), raw="real"))
        min = self._txi(Dln2SpiInterface.GET_MIN_FREQUENCY, bytearray([0]))
        max = self._txi(Dln2SpiInterface.GET_MAX_FREQUENCY, bytearray([0]))
        #fs = self._txi(Dln2SpiInterface.GET_SUPPORTED_FRAME_SIZES, bytearray([0]))
        self._tx(Dln2SpiInterface.SS_MULTI_ENABLE, bytearray([0, 1]))  #enable the one cs we have
        self._txi(Dln2SpiInterface.SET_FRAME_SIZE, bytearray([0, 8]))
        ssc = self._txi(Dln2SpiInterface.GET_SS_COUNT, bytearray([0]))  #this is missused by pico dln to init max freq and framesize 8
        print(f'min freq: {min}')
        print(f'max freq: {max}')
        print(f'cs count: {ssc}')
        if freq == "max":
            freq = max
        if freq == "min":
            freq = min
        b = bytearray([0]) + freq.to_bytes(4, 'little')
        self._tx(Dln2SpiInterface.SET_FREQUENCY, b)

    def disable(self):
        return self._tx(Dln2SpiInterface.DISABLE, bytearray([0, 0]), raw="real")

    def tx(self, buf, keeplow=0):
        # format port(u8) len(u16) attr(u8) data(lenbytes)
        b = bytearray([0, len(buf), 0, keeplow])
        b = b + buf
        return self._tx(Dln2SpiInterface.READ_WRITE, b)


class Dln2GpioInterface(Dln):
    GET_PIN_COUNT =     0x01
    SET_DEBOUNCE =      0x04
    GET_DEBOUNCE =      0x05
    PORT_GET_VAL =      0x06
    PIN_GET_VAL =       0x0B
    PIN_SET_OUT_VAL =   0x0C
    PIN_GET_OUT_VAL =   0x0D
    CONDITION_MET_EV =  0x0F
    PIN_ENABLE =        0x10
    PIN_DISABLE =       0x11
    PIN_SET_DIRECTION = 0x13
    PIN_GET_DIRECTION = 0x14
    PIN_SET_EVENT_CFG = 0x1E
    PIN_GET_EVENT_CFG = 0x1F

    EVENT_NONE =        0
    EVENT_CHANGE =      1
    EVENT_LVL_HIGH =    2
    EVENT_LVL_LOW =     3
    EVENT_CHANGE_RISING =  0x11
    EVENT_CHANGE_FALLING = 0x21
    EVENT_MASK = 0x0F

    def __init__(self, dev):
        Dln.__init__(self, dev, module=Dln.MODULE_GPIO, handle=Dln.HANDLE_GPIO)
        debug_print(f'nr of gpios: {self.getpincount()}')

    def getpincount(self):
        return self._txi( Dln2GpioInterface.GET_PIN_COUNT)

    def _txpin(self, cmd, pin, val=None):
        if val is None:
            data = bytearray([pin, 0])
        else:
            data = bytearray([pin, 0, val])

        return self._txi(cmd, data)

    class Dln2Pin():
        def __init__(self, interface, pin):
            self.inter = interface
            self.num = pin
            self.enable()

        def setirqmask(self, mask, cb):
            self.inter.dln.addgpio(self.num, self)
            if mask == 1:
                self.cb = cb
            else:
                self.cb = None
            return self.inter._txi(Dln2GpioInterface.PIN_SET_EVENT_CFG, bytearray([self.num, 0, mask, 0, 0]))

        def irqcallback(self, num, val):
            if self.cb is not None:
                self.cb(num, val)

        def enable(self):
            return self.inter._txpin(Dln2GpioInterface.PIN_ENABLE, self.num)

        def getval(self):
            return self.inter._txpin(Dln2GpioInterface.PIN_GET_VAL, self.num)

        def getdir(self):
            return self.inter._txpin(Dln2GpioInterface.PIN_GET_DIRECTION, self.num)

        def setdir(self, val):
            return self.inter._txpin(Dln2GpioInterface.PIN_SET_DIRECTION, self.num, val)

        def setval(self, val):
            return self.inter._txpin(Dln2GpioInterface.PIN_SET_OUT_VAL, self.num, val)

    def create(self, pin):
        return self.Dln2Pin(self, pin)


class Dln2I2cInterface(Dln):
    """
    Interface class for interacting with the DLN2 I2C interface.
    """

    def __init__(self, dev):
        """
        Initialize the interface with the given USB device.

        :param dev: USB device object
        """
        Dln.__init__(self, dev, module=Dln.MODULE_I2C, handle=Dln.HANDLE_I2C)
        self._initialize_i2c()

    def _initialize_i2c(self):
        """Activate I2C0 on the device."""
        self._txi(1, bytearray([0]))

    def write_i2c(self, addr, data):
        """
        Write data to I2C address.

        :param addr: I2C address
        :param data: Data to write (bytearray)
        """
        length = len(data)
        self._tx(6, bytearray([0, addr, 0, 0, 0, 0, 0, length, 0]) + data)

    def read_i2c(self, addr, length):
        """
        Read data from I2C address.

        :param addr: I2C address
        :param length: Number of bytes to read
        """
        return self._tx(7, bytearray([0, addr, 0, 0, 0, 0, 0, length, 0]))

    def write_byte_data(self, addr, reg, val):
        """
        Write byte data to a specific register at an I2C address.

        :param addr: I2C address
        :param reg: Register number
        :param val: Value to write
        """
        return self.write_i2c(addr, bytearray([reg, val]))

    def read_byte_data(self, addr, reg):
        """
        Read byte data from a specific register at an I2C address.

        :param addr: I2C address
        :param reg: Register number
        """
        self.write_i2c(addr, bytearray([reg]))
        return self.read_i2c(addr, 1)[0]


def getdefault():
    return Dlndev(usb.core.find(idVendor=Dlndev.USB_VID, idProduct=Dlndev.USB_PID))


def main():
    dev = getdefault()

    if not dev:
        print("Device not found")
        exit(1)

    #    # Initialize device
    gp = Dln2GpioInterface(dev)
    led = gp.create(25)
    led.setdir(1)
    led.setval(1)
    if led.getval() != 1:
        print("led wrong set")
    time.sleep(0.5)
    led.setval(0)
    if led.getval() != 0:
        print(f'led get 0: {led.getval()}')
    spi = Dln2SpiInterface(dev)
    dat = bytearray([0xff,0xaf,0xaf,0xfe, 0, 1, 4,0xca,0xfe])
    ret = spi.tx(dat)
    #spi.disable()
    if ret != dat:
        print("WRONG")
        print(ret)
    dln2i2c = Dln2I2cInterface(dev)
    return spi, gp, dln2i2c


def find_device_by_serial(serial_number):
    # Find all USB devices
    devices = usb.core.find(find_all=True)

    # Iterate through devices and check their serial numbers
    for dev in devices:
        try:
            # Get the serial number string descriptor
            ser_num = usb.util.get_string(dev, dev.iSerialNumber)

            # Check if the serial number matches
            if ser_num == serial_number:
                return Dlndev(dev)

            # If we've reached here, it's not the device we're looking for
            continue

        except:
            # Some devices don't have a serial number
            continue

    # If we reach here, no matching device was found
    return None


if __name__ == "__main__":
    #spi, gp, ii= main()
    all = usb.core.find(find_all=True)
    for x in all:
        try:
            #if x.iSerialNumber != 0:
            print(x.serial_number)
        except:
            print("dod not work")
