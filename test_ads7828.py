import smbus2 as smbus
import time

# pip3 install smbus2 on RPi, once I got the AI to use smbus2, this fixed a run time error

# ADS7828 default I2C address is 0x48 (might be 0x49 depending on your setup)
ADS7828_I2C_ADDR = 0x48

# Control byte bits for channel selection
CHANNEL_CONTROL = [
    0x80,  # Channel 0
    0xC0,  # Channel 1
    0x90,  # Channel 2
    0xD0,  # Channel 3
    0xA0,  # Channel 4
    0xE0,  # Channel 5
    0xB0,  # Channel 6
    0xF0,  # Channel 7
]

# Reference voltage (change if you use a different reference)
VREF = 2.5

def read_adc(bus, channel):
    if channel < 0 or channel > 7:
        raise ValueError("Channel must be between 0 and 7")

    # control_byte = CHANNEL_CONTROL[channel] | 0x04  # Single-ended, power-down between A/D conversions
    # AI says power-down between A/D conversions (power what down?), reading the datasheet, it seems 0x04 turns off ref but leaves A/D on which I would not think is a good idea
    # ends up this was a nasty bug that was causing the output to be understated by about 28%, an amount that was very confusing
    #control_byte = CHANNEL_CONTROL[channel] | 0x0C  # changed to leave ref, A/D powered up to test HW because A/D output value was low and not obvious why, this fixed the bad readings
    control_byte = CHANNEL_CONTROL[channel] | 0x08 # power-down A/D, keep ref on resulted in good readings

    bus.write_byte(ADS7828_I2C_ADDR, control_byte)
    time.sleep(0.01)  # Wait for conversion (~10ms is safe)
    # ~10ms may be safe - you need to read the datasheet to understand this is intertwined with the hardware choices made on decoupling the on chip ref
    # and turning on the A/D and the mode you are in, or maybe you can go faster
    data = bus.read_i2c_block_data(ADS7828_I2C_ADDR, control_byte, 2)

    # print(f"data[0] {data[0]} / data[1] {data[1]}") # added to see why the voltages were wrong
    # print(f"data[0] 0x{data[0]:X} / data[1] 0x{data[1]:X}") # added to see why the voltages were wrong
    # raw_val = ((data[0] << 8) | data[1]) >> 4 # >> 4 is a bad bug AI put in that throws away data, needed to read the datasheet to understand the output bytes
    raw_val = ((data[0] << 8) | data[1]) # this works
    # raw_val = ((data[0] << 8) + data[1]) # this also works

    voltage = (raw_val / 4096.0) * VREF # AI put 4096, I think it should be 4095, but a minor issue
    return raw_val, voltage

def main():
    bus = smbus.SMBus(1)  # For Raspberry Pi, bus 1 is typical, 
    print("Testing ADS7828 ADC")
    for ch in range(8):
        raw, volt = read_adc(bus, ch)
        if ch == 0: # on the test unit, a TMP36 is on the input
            TmpC = (volt - 0.5) * 100
            print(f"Channel {ch}: Raw={raw:4d}, Voltage={volt:.3f} V, Temp(TMP36)={(TmpC):.1f} C, {(TmpC * 9 / 5) + 32:.1f} F")
        elif ch == 1:
            # on the test unit, a 10K / 10K divider is on the input and it is connected to the 3.3V supply
            print(f"Channel {ch}: Raw={raw:4d}, Voltage={volt * 2:.3f} V")
        elif ch in [2, 3, 4]:
            # on the test unit, a 154K / 10K or 147K + 20K trimmer / 10K divider is on the input and it is connected to the 3.3V supply
            # these values are used to give a full scale 4095 at 40.95V
            print(f"Channel {ch}: Raw={raw:4d}, Voltage={raw / 100:.3f} V")
        else:
            print(f"Channel {ch}: Raw={raw:4d}, Voltage={volt:.3f} V")
    print("Test complete.")

if __name__ == "__main__":
    main()

# Tried to write this "vibe coding" in Copilot. The ADS7828 is over 20 years old and everything you need for it is on the public Internet.
# Started with:
# Write a python program to test a ADS7828
# Added because it was using the smbus lib (smbus2), and it was messing up the referance and not scaling the voltage correctly:
# Use the smbus2 library, the internal referance and output raw and voltage values
# Noe AI used the smbus2 lib, but did not fix any of the other issues.
# So I went through the ADS7828 datasheet, learned how the chip works and fixed the bugs that AI put in. 
