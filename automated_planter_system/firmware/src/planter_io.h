// Pins for zones and tanks: the ESP32's own, or more on the I2C bus when it runs out.
//
//   0-39            an ESP32 GPIO
//   XPIN(chip, n)   pin n (0-15: GPA0-7 then GPB0-7) of an MCP23017 expander at I2C address 0x20 + chip (0-7).
//                   For more valves (DRV8833 inputs) and float switches.
//   ADC_CH(chip, c) input c (0-3) of an ADS1115 converter at I2C address 0x48 + chip (0-3). For more soil sensors.
//
// Both sit on the clock module's I2C bus (SDA 21, SCL 22) and are powered from 3.3 V. They keep their outputs while
// the ESP32 sleeps, and the DRV8833s' shared sleep pin is held low then, so no valve can move. Small drivers
// written here (a few registers each), so no extra libraries are needed. Included by main.cpp.
#pragma once
#include <Arduino.h>
#include <Wire.h>

#define XPIN(chip, n) (100 + (chip) * 16 + (n))
#define ADC_CH(chip, c) (300 + (chip) * 4 + (c))
#define IS_XPIN(p) ((p) >= 100 && (p) < 228)
#define IS_ADC_CH(p) ((p) >= 300 && (p) < 316)

// ---------------------------------------------------------------- MCP23017
struct Expander { bool ready; uint8_t iodir[2], pullup[2], olat[2]; };
static Expander expanders[8];

static bool mcpWrite(uint8_t chip, uint8_t reg, uint8_t v) {
  Wire.beginTransmission(0x20 + chip);
  Wire.write(reg);
  Wire.write(v);
  return Wire.endTransmission() == 0;
}
static int mcpRead(uint8_t chip, uint8_t reg) {
  Wire.beginTransmission(0x20 + chip);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0 || Wire.requestFrom((uint8_t)(0x20 + chip), (uint8_t)1) != 1) return -1;
  return Wire.read();
}
// Registers (IOCON.BANK = 0): IODIRA 0x00, GPPUA 0x0C, GPIOA 0x12, OLATA 0x14; the B port is the next address.
static Expander *mcp(uint8_t chip) {
  Expander &e = expanders[chip];
  if (!e.ready) {
    int a = mcpRead(chip, 0x00), b = mcpRead(chip, 0x01);
    if (a < 0 || b < 0) { log_e("No MCP23017 at 0x%02X", 0x20 + chip); return nullptr; }
    e.iodir[0] = a; e.iodir[1] = b;
    e.pullup[0] = mcpRead(chip, 0x0C); e.pullup[1] = mcpRead(chip, 0x0D);
    e.olat[0] = mcpRead(chip, 0x14); e.olat[1] = mcpRead(chip, 0x15);
    e.ready = true;
  }
  return &e;
}

// ---------------------------------------------------------------- ADS1115
// One single-shot conversion of input c against ground, ±4.096 V range (0.125 mV per step), 128 samples/s.
static int adsReadMv(uint8_t chip, uint8_t c) {
  uint8_t addr = 0x48 + chip;
  uint16_t cfg = 0x8000 | ((4 + c) << 12) | (1 << 9) | (1 << 8) | (4 << 5) | 3;
  Wire.beginTransmission(addr);
  Wire.write(0x01);
  Wire.write(cfg >> 8);
  Wire.write(cfg & 0xFF);
  if (Wire.endTransmission() != 0) { log_e("No ADS1115 at 0x%02X", addr); return -1; }
  delay(9);
  Wire.beginTransmission(addr);
  Wire.write(0x00);
  if (Wire.endTransmission(false) != 0 || Wire.requestFrom(addr, (uint8_t)2) != 2) return -1;
  int16_t raw = (Wire.read() << 8) | Wire.read();
  return raw < 0 ? 0 : raw / 8;
}

// ---------------------------------------------------------------- the same calls for any pin
void ioMode(int pin, uint8_t mode) {
  if (pin < 0) return;
  if (pin < 100) { pinMode(pin, mode); return; }
  if (!IS_XPIN(pin)) return;
  uint8_t chip = (pin - 100) / 16, n = (pin - 100) % 16, port = n / 8, bit = 1 << (n % 8);
  Expander *e = mcp(chip);
  if (!e) return;
  uint8_t dir = mode == OUTPUT ? e->iodir[port] & ~bit : e->iodir[port] | bit;
  uint8_t pu = mode == INPUT_PULLUP ? e->pullup[port] | bit : e->pullup[port] & ~bit;
  if (mode == OUTPUT && (e->olat[port] & bit)) { e->olat[port] &= ~bit; mcpWrite(chip, 0x14 + port, e->olat[port]); }  // start low
  if (pu != e->pullup[port]) { e->pullup[port] = pu; mcpWrite(chip, 0x0C + port, pu); }
  if (dir != e->iodir[port]) { e->iodir[port] = dir; mcpWrite(chip, 0x00 + port, dir); }
}

void ioWrite(int pin, uint8_t level) {
  if (pin < 0) return;
  if (pin < 100) { digitalWrite(pin, level); return; }
  if (!IS_XPIN(pin)) return;
  uint8_t chip = (pin - 100) / 16, n = (pin - 100) % 16, port = n / 8, bit = 1 << (n % 8);
  Expander *e = mcp(chip);
  if (!e) return;
  uint8_t v = level ? e->olat[port] | bit : e->olat[port] & ~bit;
  if (v != e->olat[port]) { e->olat[port] = v; mcpWrite(chip, 0x14 + port, v); }
}

int ioRead(int pin) {
  if (pin < 0) return -1;
  if (pin < 100) return digitalRead(pin);
  if (!IS_XPIN(pin)) return -1;
  uint8_t chip = (pin - 100) / 16, n = (pin - 100) % 16;
  if (!mcp(chip)) return -1;
  int v = mcpRead(chip, 0x12 + n / 8);
  return v < 0 ? -1 : (v >> (n % 8)) & 1;
}

// Millivolts on an analog input: an ESP32 ADC1 pin (32-39; ADC2 pins don't work while Wi-Fi is on) or an ADS1115
// input. Averages 8 samples. -1 if it can't be read.
int ioReadMv(int pin) {
  if (pin < 0) return -1;
  int32_t sum = 0;
  for (int i = 0; i < 8; i++) {
    int mv;
    if (pin < 100) mv = analogReadMilliVolts(pin);
    else if (IS_ADC_CH(pin)) mv = adsReadMv((pin - 300) / 4, (pin - 300) % 4);
    else return -1;
    if (mv < 0) return -1;
    sum += mv;
    if (pin < 100) delay(2);
  }
  return sum / 8;
}
