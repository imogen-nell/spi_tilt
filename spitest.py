import time
import spidev
import RPi.GPIO as GPIO

#######
SW_RESET	    = [0xB4, 0x00, 0x20, 0x98]
WHOAMI  	    = [0x40, 0x00, 0x00, 0x91]
CS_TILT 		= 18 #pin12 is BCM 18
READ_STAT 		= [0x18, 0x00, 0x00, 0xE5]
MODE_1   		= [0xB4, 0x00, 0x00, 0x1F]
READ_CMD  		= [0x34, 0x00, 0x00, 0xDF]
WAKE_UP   		= [0xB4, 0x00, 0x00, 0x1F]
ANG_CTRL  		= [0xB0, 0x00, 0x1F, 0x6F]
READ_CURR_BANK  = [0x7C, 0X00, 0X00, 0XB3]
SW_TO_BNK0		= [0xFC, 0x00, 0x00, 0x73]
ANG_X			= [0x24, 0x00, 0x00, 0xC7]
ANG_Y			= [0x28, 0x00, 0x00, 0xCD]
ANG_Z			= [0x2C, 0x00, 0x00, 0xCB]
#######
bus = 1
device = 0
# Enable SPI #
spi = spidev.SpiDev()
spi.open(bus, device)
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(CS_TILT, GPIO.OUT)
#begin with CS high
GPIO.output(CS_TILT, 1) 
spi.max_speed_hz = 2000000 #2-4 MHz
spi.mode = 0
time.sleep(0.05)
##############

#Write bytes to the SPI device
def write(data):
	GPIO.output(CS_TILT, 0) 
	spi.writebytes(data)
	time.sleep(0.02)
	GPIO.output(CS_TILT, 1)
	# time.sleep(0.02)
	return

#Read bytes from the SPI device
def read(msg, nbytes=0):
	if nbytes == 0:
		nbytes = len(msg)
	#request
	GPIO.output(CS_TILT, 0)
	spi.writebytes(msg)
	time.sleep(0.02)
	print("msg:", msg)
	GPIO.output(CS_TILT, 1)
	time.sleep(0.01)
	#response
	GPIO.output(CS_TILT, 0)
	ret = spi.readbytes(nbytes)
	time.sleep(0.02)
	GPIO.output(CS_TILT, 1)
	return ret

def xfer(data):
	GPIO.output(CS_TILT, 0)
	ret = spi.xfer(data)
	time.sleep(0.02)
	GPIO.output(CS_TILT, 1)
	return ret

def start_up():
	print("*****start up sequence *****")
	GPIO.output(CS_TILT, 1)
	xfer(SW_TO_BNK0)
	#wake up from power down 
	xfer(SW_RESET)
	#SET MEASUREMENT MODE
	xfer(MODE_1)
	#write ANG_CTRL to enable angl outputs
	xfer(ANG_CTRL)
	#clear and read STATUS 
	dummyread0 = xfer(READ_STAT)
	status = xfer(READ_STAT)

	print("status:", status)
	#print("read0:", dummyread0)
	time.sleep(0.025)
	print("*****start up sequence complete*****")

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

#read response as HEX
def toHex(msg):
	return [hex(num) for num in msg]

#Read the WHOAMI register, built in init request (run at start)
def whoami():
    GPIO.output(CS_TILT, 0)
    time.sleep(0.001)
	#discard first read
    dummy_32 = xfer(WHOAMI)  # Ask who am I
    time.sleep(0.01)

    whoami_register = xfer( WHOAMI)  # Ask again
    time.sleep(0.01)

    GPIO.output(CS_TILT, 1)

    return whoami_register

try: 	
	start_up()
	time.sleep(1)
	while True:
		i = whoami()
		print("whoami responce:", toHex(i))
		print("reading:", WHOAMI)
		print("reading:", toHex(WHOAMI))
		print("should be reading:", [0x40, 0x00, 0x00, 0x91])
		readI = read(WHOAMI, 4)
		if i!=readI:
			print("whoami read:", toHex(readI))

		i=toHex(i)
		print("OP", i[0])
		print("return stat", i[1])
		print("data", i[2])
		print("result CRC: ", i[3])
		print("full crc: ", calculate_crc(0x40000091))

		time.sleep(1)
	
except KeyboardInterrupt:
	spi.close()
