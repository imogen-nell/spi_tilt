import time
import spidev
import RPi.GPIO as GPIO

#######
SW_RESET  = [0xB4, 0x00, 0x20, 0x98]
WHOAMI    = [0x40, 0x00, 0x00, 0x91]
CS_TILT   = 18 
SPI_TILT  = 0 ##TODO wtf is this 
READ_STAT = [0x18, 0x00, 0x00, 0xE5]
MODE_1    = [0xB4, 0x00, 0x00, 0x1F]
READ_CMD  = [0x34, 0x00, 0x00, 0xDF]
WAKE_UP   = [0xB4, 0x00, 0x00, 0x1F]
ANG_CTRL  = [0xB0, 0x00, 0x1F, 0x6F]
#######
bus = 0
device = 0
# Enable SPI #
spi = spidev.SpiDev()
spi.open(bus, device)
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
GPIO.output(18,1) 
spi.max_speed_hz = 2000000 #2-4 MHz
spi.mode = 0
time.sleep(0.0005)
##############

def write(data):
	GPIO.setmode(GPIO.BCM)
	GPIO.output(CS_TILT, 0) #pin12 is BCM 18
	spi.write(data)
	GPIO.output(CS_TILT, 1)
	time.sleep(0.05)

def read(data, nbytes):
	msg = bytearray()
	msg.append(data)
	GPIO.output(CS_TILT, 0)
	spi.write(msg)
	print("msg:", msg)
	ret = spi.read(nbytes)
	GPIO.output(CS_TILT, 1)
	return ret

def read_xfer(data):
	GPIO.output(CS_TILT, 0)
	ret = spi.xfer(data)
	GPIO.output(CS_TILT, 1)
	return ret

def start_up():

	#wake up from power down 
	#SW RESET
	spi.xfer(SW_RESET)
	stat_reg = spi.xfer(READ_STAT)
	print("stat register:", stat_reg)

	# Set SPI speed and mode
	time.sleep(.01)

	#SET MEASUREMENT MODE
	spi.xfer(MODE_1)
	time.sleep(0.025)
	print("mode:", spi.xfer([ 0x0D,0x10, 16, 14]))

	#write ANG_CTRL to enable angl outputs
	spi.xfer(ANG_CTRL)
	time.sleep(.025)

	#clear status
	#read STATUS 
	print("status:", spi.xfer(READ_STAT))
def calculate_crc(data):
    CRC = 0xFF
    for BitIndex in range(31, 7, -1):
        BitValue = (data >> BitIndex) & 0x01
        CRC = crc8(BitValue, CRC)
    CRC = ~CRC & 0xFF
    return CRC

def crc8(BitValue, CRC):
    Temp = CRC & 0x80
    if BitValue == 0x01:
        Temp ^= 0x80
    CRC <<= 1
    if Temp > 0:
        CRC ^= 0x1D
    return CRC
def whoami():
    dummy_32 = 0
    whoami_register = 0
    GPIO.output(CS_TILT, 0)
    time.sleep(0.001)

    dummy_32 = read_xfer(WHOAMI)  # Ask who am I
    time.sleep(0.01)

    whoami_register = read_xfer( WHOAMI)  # Ask again
    time.sleep(0.01)

    GPIO.output(CS_TILT, 1)

    return whoami_register

try: 	
	start_up()
	time.sleep(1)
	while True:
		data = 0x040000F7
		print("CrC:", hex(calculate_crc(data)))
		print("whoami:", whoami())
		time.sleep(0.05)
		print("read:", read_xfer(READ_STAT))
		time.sleep(0.05)
		print("read long:", read_xfer([0x180000E5]))
except KeyboardInterrupt:
	spi.close()
