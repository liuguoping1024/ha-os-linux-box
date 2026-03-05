# -*- coding: UTF-8 -*-

import time

try:
    import bflb_path
except ImportError:
    from libs import bflb_path
from libs import bflb_utils
from libs import bflb_proto as pt
from libs import bflb_interface_uart as itf

__all__ = [
    "mfg_mode_table", "mac80211b_drop_ctn", "mac80211b_g_pre_type", "mac80211g_drop_ctn",
    "mac80211n_drop_ctn", "mac80211_channel", "mac80211_channel_40", "mac80211ax_mcs_wb03",
    "mac80211ax_coding", "mac80211ax_heltf_gi", "dtim_drop_ctn", "bl60x_tx_dur", "bl60x_tx_duty",
    "bl60x_a0_power_table", "bl60x_cw_test_power_table", "BL60xTxFrameConfiger",
    "Bl60xMfgMisc1Observer", "Bl60xMfgMisc", "btn_ble_tx_power", "btn_ble_tx_start",
    "btn_ble_rx_start", "btn_ble_stop", "btn_11b_start", "btn_11g_start", "btn_11n_start",
    "btn_11ax_start_wb03", "tx_enable", "tx_disable", "rx_start", "rx_stop", "rx_sen_get",
    "pds_enter_rtc", "pds_enter_forever", "hbn_enter", "CliInfUart"
]

CliInfUart = itf.CliInfUart

mfg_mode_table = ('Normal', 'Test(CW)')
mac80211b_drop_ctn = ("1Mbps", "2Mbps", "5.5Mbps", "11Mbps")
mac80211b_pre_type = ('Long Preamble', 'Long Preamble', 'Long Preamble', 'Long Preamble')
mac80211b_g_pre_type = ('Long Preamble', 'Long Preamble')
mac80211g_drop_ctn = ('6Mbps', '9Mbps', '12Mbps', '18Mbps', '24Mbps', '36Mbps', '48Mbps', '54Mbps')
mac80211n_drop_ctn = ('MCS0', 'MCS1', 'MCS2', 'MCS3', 'MCS4', 'MCS5', 'MCS6', 'MCS7')
mac80211_channel = ('1(2412)', '2(2417)', '3(2422)', '4(2427)', '5(2432)', '6(2437)', '7(2442)',
                    '8(2447)', '9(2452)', '10(2457)', '11(2462)', '12(2467)', '13(2472)',
                    '14(2484)')
mac80211_channel_40 = ('3(2422)', '4(2427)', '5(2432)', '6(2437)', '7(2442)', '8(2447)', '9(2452)',
                       '10(2457)', '11(2462)', '14(2484)')
mac80211ax_mcs_wb03 = ('MCS0', 'MCS1', 'MCS2', 'MCS3', 'MCS4', 'MCS5', 'MCS6', 'MCS7', 'MCS8',
                       'MCS9', 'DCM-MCS0', 'DCM-MCS1', 'DCM-MCS3', 'DCM-MCS4', 'ER-MCS0',
                       'ER-MCS1', 'ER-MCS2')
mac80211ax_coding = ["BCC", "LDPC"]
mac80211ax_heltf_gi = ["2x HELTF+0.8us GI", "2x HELTF+1.6us GI", "4x HELTF+3.2us GI"]
mac80211ax_bw = ["20M", "40M"]
dtim_drop_ctn = ('1', '2', '3', '4', '5', '6', '7', '8', '9')
bl60x_tx_dur = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')
bl60x_tx_duty = ('50%', '100%')
bl60x_a0_power_table = ('Auto', '23dbm', '22dbm', '21dbm', '20dbm', '19dbm', '18dbm', '17dbm',
                        '16dbm', '15dbm', '14dbm', '13dbm', '12dbm', '11dbm', '10dbm')
bl60x_cw_test_power_table = ('Auto', '20dbm', '19dbm', '18dbm', '17dbm', '16dbm', '15dbm', '14dbm',
                             '13dbm', '12dbm', '11dbm', '10dbm', '9dbm', '8dbm', '7dbm', '6dbm')


def itf_open(uart_dev, itf_no):
    bflb_utils.printf("OPEN : (%s)" % (itf_no))
    return uart_dev.open(itf_no)


def itf_close(uart_dev):
    uart_dev.close()


def itf_send(uart_dev, str_data):
    if uart_dev.is_open() is False:
        bflb_utils.printf("Please Open COM")
    else:
        sb = bytes(str_data + '\r', encoding="ascii")
        uart_dev.write(sb)


def btn_ble_tx_power(uart_dev, hex_tx_power):
    bflb_utils.printf("ble tx start: (0x%s)" % (hex_tx_power))
    proto_frame = pt.cli_ble_tx_power(hex_tx_power)
    bflb_utils.printf(proto_frame)
    itf_send(uart_dev, proto_frame)


def btn_ble_tx_start(uart_dev, hex_tx_channel, hex_length_of_test_data, hex_packet_payload):
    bflb_utils.printf("ble tx start: (0x%s), (0x%s), (0x%s)" %
                      (hex_tx_channel, hex_length_of_test_data, hex_packet_payload))
    proto_frame = pt.cli_ble_tx_start(hex_tx_channel, hex_length_of_test_data, hex_packet_payload)
    bflb_utils.printf(proto_frame)
    itf_send(uart_dev, proto_frame)


def btn_ble_rx_start(uart_dev, hex_rx_channel):
    bflb_utils.printf("ble rx start: (0x%s)" % (hex_rx_channel))
    proto_frame = pt.cli_ble_rx_start(hex_rx_channel)
    bflb_utils.printf(proto_frame)
    itf_send(uart_dev, proto_frame)


def btn_ble_stop(uart_dev):
    bflb_utils.printf("ble stop")
    proto_frame = pt.cli_ble_stop()
    bflb_utils.printf(proto_frame)
    itf_send(uart_dev, proto_frame)


def btn_11b_start(uart_dev, rate, pre_type):
    bflb_utils.printf("btn_11b_start: (%s), (%s)" % (rate, pre_type))
    rate_idx = mac80211b_drop_ctn.index(rate)
    short_type = mac80211b_g_pre_type.index(pre_type)
    proto_frame = pt.cli_proto_tx_11b(rate_idx, short_type)
    bflb_utils.printf(proto_frame)
    itf_send(uart_dev, proto_frame)


def btn_11g_start(uart_dev, rate, pre_type):
    bflb_utils.printf("btn_11g_start: (%s), (%s)" % (rate, pre_type))
    rate_idx = mac80211g_drop_ctn.index(rate)
    short_type = mac80211b_g_pre_type.index(pre_type)

    proto_frame = pt.cli_proto_tx_11g(rate_idx, short_type)
    bflb_utils.printf(proto_frame)
    itf_send(uart_dev, proto_frame)


def btn_11n_start(uart_dev, mcs, gi, mod, bw, coding=None):
    bflb_utils.printf("btn_11n_start: (%s), (%s), (%s), (%s), (%s)" % (mcs, gi, mod, bw, coding))
    mcs_idx = mac80211n_drop_ctn.index(mcs)
    if coding:
        coding_idx = mac80211ax_coding.index(coding)
    else:
        coding_idx = ""
    proto_frame = pt.cli_proto_tx_11n(mcs_idx, gi, mod, bw, coding_idx)
    bflb_utils.printf(proto_frame)
    itf_send(uart_dev, proto_frame)


def btn_11ax_start_wb03(uart_dev, mcs, coding, heltf_gi, bw):
    bflb_utils.printf("btn_11ax_start: (%s), (%s), (%s), (%s)" % (mcs, coding, heltf_gi, bw))
    mcs_idx = mac80211ax_mcs_wb03.index(mcs)
    coding_idx = mac80211ax_coding.index(coding)
    heltf_gi_idx = mac80211ax_heltf_gi.index(heltf_gi)
    bw_idx = mac80211ax_bw.index(bw)

    proto_frame = pt.cli_proto_tx_11ax_wb03(mcs_idx, coding_idx, heltf_gi_idx, bw_idx)
    bflb_utils.printf(proto_frame)
    itf_send(uart_dev, proto_frame)


def tx_enable(uart_dev):
    proto_frame = pt.cli_tx_enable()
    if proto_frame is not None:
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)


def tx_disable(uart_dev):
    proto_frame = pt.cli_tx_disable()
    if proto_frame is not None:
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)


def rx_start(uart_dev):
    proto_frame = pt.cli_rx_start()
    if proto_frame is not None:
        itf_send(uart_dev, proto_frame)


def rx_stop(uart_dev):
    proto_frame = pt.cli_rx_stop()
    if proto_frame is not None:
        itf_send(uart_dev, proto_frame)


def rx_sen_get(uart_dev):
    proto_frame = pt.cli_rx_sen_get()
    if proto_frame is not None:
        itf_send(uart_dev, proto_frame)


def pds_enter_rtc(uart_dev, wakeup_tim, dtim, dtim_cnt):
    int_wakeup_tim = int(wakeup_tim)
    proto_frm = pt.cli_proto_wakeup_keep_time_setting(int_wakeup_tim)
    bflb_utils.printf(proto_frm)
    itf_send(uart_dev, proto_frm)

    int_dtim = int(dtim)
    int_dtim_cnt = int(dtim_cnt)
    proto_frm = pt.cli_proto_pds(int_dtim, int_dtim_cnt)
    bflb_utils.printf(proto_frm)
    itf_send(uart_dev, proto_frm)


def pds_enter_forever(uart_dev):
    proto_frm = pt.cli_proto_pds_forever()
    bflb_utils.printf(proto_frm)
    itf_send(uart_dev, proto_frm)


def hbn_enter(uart_dev, hbn_sec):
    proto_frm = pt.cli_proto_hbn(hbn_sec)
    bflb_utils.printf(proto_frm)
    itf_send(uart_dev, proto_frm)


class BL60xTxFrameConfiger(object):

    def __init__(self):
        self._tx_frm_len = 500
        self._tx_frm_freq = 100

    def set_wifi_mode(self, mode, speed):
        tx_frm_len_list = {
            "1Mbps": 101,
            "2Mbps": 202,
            "5.5Mbps": 556,
            "11Mbps": 1111,
            "6Mbps": 360,
            "9Mbps": 540,
            "12Mbps": 720,
            "18Mbps": 1080,
            "24Mbps": 1440,
            "36Mbps": 2160,
            "48Mbps": 2880,
            "54Mbps": 3240,
            "MCS0": 384,
            "MCS1": 767,
            "MCS2": 1151,
            "MCS3": 1534,
            "MCS4": 2301,
            "MCS5": 3068,
            "MCS6": 3452,
            "MCS7": 3835
        }
        tx_frm_freq_list = {
            "1Mbps": 500,
            "2Mbps": 500,
            "5.5Mbps": 500,
            "11Mbps": 500,
            "6Mbps": 1000,
            "9Mbps": 1000,
            "12Mbps": 1000,
            "18Mbps": 1000,
            "24Mbps": 1000,
            "36Mbps": 1000,
            "48Mbps": 1000,
            "54Mbps": 1000,
            "MCS0": 1000,
            "MCS1": 1000,
            "MCS2": 1000,
            "MCS3": 1000,
            "MCS4": 1000,
            "MCS5": 1000,
            "MCS6": 1000,
            "MCS7": 1000
        }
        self._tx_frm_len = tx_frm_len_list.get(speed, "500")
        self._tx_frm_freq = tx_frm_freq_list.get(speed, "500")

    def get_frm_len(self):
        return self._tx_frm_len

    def get_frm_freq(self):
        return self._tx_frm_freq


class Bl60xMfgMisc1Observer(object):

    def __init__(self, frame):
        self._cur_cmd = None
        self._cur_oper = None
        self._cur_args = None
        self._vs_func = None
        self.cmd_queue = []
        self.cmd_queue_status = 0
        self.frame = frame

    """It run at rx thread"""

    def obs_handle(self, data):
        val = []
        if data[0:4] == '#*#*':
            bflb_utils.printf("obs_handle [%s]" % (data))
            ## begin is cmd
            cmd = data[4:]
            val = cmd.split(':')
            if val[0] == "channel":
                self._update_chan_ui(val[1])
            elif val[0] == "power":
                self._update_pwr_ui(val[1])
            elif val[0] == "duty":
                self._update_duty_ui(val[1])
            elif val[0] == "capcode":
                self._update_capcode_ui(val[1])
            elif val[0] == "mfgmode":
                self._update_mfgmode_ui(val[1])

    def _cur_oper_done(self):
        self._cur_cmd = None
        self._cur_oper = None
        self._cur_args = None
        self._vs_func = None
        if len(self.cmd_queue) != 0:
            func = self.cmd_queue.pop(0)
            func()
        else:
            self.cmd_queue_status = 0

    def _is_cur_oper_done(self):
        if self._cur_cmd is None and self._cur_oper is None and self._cur_args is None and self._vs_func is None:
            return True
        else:
            return False

    def channel_get(self, oper, args):

        self._cur_cmd = 'channel'
        self._cur_oper = oper
        self._cur_args = args
        self._vs_func = self._channel_vs

    """It runs at rx thread"""

    def _channel_vs(self, real_ch, setting_ch):
        idx = setting_ch.find('(')
        gui_ch = setting_ch[idx + 1:-1]
        #bflb_utils.printf("_channel_vs %s:%s" %(real_ch, gui_ch))
        if real_ch != gui_ch:
            return True
        else:
            return False

    def power_get(self, oper, args):
        self._cur_cmd = 'power'
        self._cur_oper = oper
        self._cur_args = args
        self._vs_func = self._power_vs

    """It runs at rx thread"""

    def _power_vs(self, real_p, setting_p):
        idx = setting_p.find('dbm')
        gui_p = setting_p[:idx]
        #bflb_utils.printf("_power_vs %s:%s" %(real_p, gui_p))
        if real_p != gui_p:
            return True
        else:
            return False

    def duty_get(self, oper, args):
        self._cur_cmd = 'duty'
        self._cur_oper = oper
        self._cur_args = args
        self._vs_func = self._duty_vs

    """It runs at rx thread"""

    def _duty_vs(self, real_d, setting_d):
        idx = setting_d.find('%')
        gui_d = setting_d[:idx]
        #bflb_utils.printf("_power_vs %s:%s" %(real_p, gui_p))
        if real_d != gui_d:
            return True
        else:
            return False

    def capcode_get(self, oper, args):
        self._cur_cmd = 'capcode'
        self._cur_oper = oper
        self._cur_args = args
        self._vs_func = self._capcode_vs

    """It runs at rx thread"""

    def _capcode_vs(self, real_d, setting_d):
        #bflb_utils.printf("_capcode_vs %s:%s" %(real_d, setting_d))
        if real_d != setting_d:
            return True
        else:
            return False

    def mfgmode_get(self, oper, args):
        self._cur_cmd = 'mfgmode'
        self._cur_oper = oper
        self._cur_args = args
        self._vs_func = self._mfgmode_vs

    """It runs at rx thread"""

    def _mfgmode_vs(self, real_mode, setting_mode):
        # bflb_utils.printf("_mfgmode_vs %s:%s" %(real_d, setting_d))
        if real_mode != setting_mode:
            return True
        else:
            return False

    def _chan_to_idx(self, real_ch):
        del_ch = 2472 - int(real_ch)
        if del_ch < 0:
            ch_idx_i = 14
        else:
            ch_idx_i = 13 - (del_ch // 5)
        return ch_idx_i

    def _update_chan_ui(self, real_ch):
        # ch = self.frame.choice_channel.GetStringSelection()
        ch_idx_i = self._chan_to_idx(real_ch)
        combo_val = str(ch_idx_i) + '(' + real_ch + ')'
        # ch.Update(combo_val, mac80211_channel)
        try:
            self.frame.combobox_channel.setCurrentText(combo_val)
        except Exception as e:
            #bflb_utils.printf(e)
            pass

    def _update_pwr_ui(self, real_pwr):
        # pwr = self.frame.choice_power.GetStringSelection()
        # pwr.Update(real_pwr + 'dbm', bl60x_a0_power_table)
        try:
            self.frame.combobox_power.setCurrentText(real_pwr + 'dbm')
        except Exception as e:
            #bflb_utils.printf(e)
            pass

    def _update_duty_ui(self, real_duty):
        #duty = self.frame.choice_txduty.GetStringSelection()
        #duty.Update(real_duty + '%', bl60x_tx_duty)
        try:
            self.frame.combobox_txduty.setCurrentText(real_duty + '%')
        except Exception as e:
            #bflb_utils.printf(e)
            pass

    def _update_capcode_ui(self, real_val):
        # capcode = self.frame.text_capcode.GetValue()
        # capcode.Update(real_val,)
        try:
            self.frame.text_capcode.setText(real_val)
        except Exception as e:
            #bflb_utils.printf(e)
            pass

    def _update_mfgmode_ui(self, real_val):
        # mfg_mode = self.frame.choice_mode.GetStringSelection()
        # mfg_mode.Update(mfg_mode_table[int(real_val)], mfg_mode_table)
        try:
            self.frame.combobox_mode.setCurrentText(mfg_mode_table[int(real_val)])
        except Exception as e:
            #bflb_utils.printf(e)
            pass

        try:
            mode = self.frame.combobox_mode.currentText()
        except Exception as e:
            #bflb_utils.printf(e)
            pass

        if mode == "Normal":
            try:
                self.frame.button_11b_start.setEnabled(True)
                self.frame.button_11g_start.setEnabled(True)
                self.frame.button_11n_start.setEnabled(True)
                self.frame.button_11b_stop.setEnabled(True)
                self.frame.button_11g_stop.setEnabled(True)
                self.frame.button_11n_stop.setEnabled(True)
                self.frame.button_rx_start.setEnabled(True)
                self.frame.button_rx_stop.setEnabled(True)
                self.frame.button_rx_recv_frm_cnt.setEnabled(True)
                self.frame.checkbox_pds.setEnabled(True)
                self.frame.button_pds_start.setEnabled(True)
                self.frame.button_hbn_start.setEnabled(True)
            except Exception:
                pass
        else:
            try:
                self.frame.button_11b_start.setEnabled(False)
                self.frame.button_11g_start.setEnabled(False)
                self.frame.button_11n_start.setEnabled(False)
                self.frame.button_11b_stop.setEnabled(False)
                self.frame.button_11g_stop.setEnabled(False)
                self.frame.button_11n_stop.setEnabled(False)
                self.frame.button_rx_start.setEnabled(False)
                self.frame.button_rx_stop.setEnabled(False)
                self.frame.button_rx_recv_frm_cnt.setEnabled(False)
                self.frame.checkbox_pds.setEnabled(False)
                self.frame.button_pds_start.setEnabled(False)
                self.frame.button_hbn_start.setEnabled(False)
            except Exception:
                pass

    def _cmd_queue_chan_update(self, uart_dev):
        try:
            ch_elem_var = self.frame.combobox_channel.currentText()
            self.channel_get(self._update_chan_ui, ch_elem_var)
            itf_send(uart_dev, pt.cli_proto_channel_get())
        except Exception as e:
            #bflb_utils.printf(e)
            pass

    def _cmd_queue_pwr_update(self, uart_dev):
        try:
            pwr_elem_var = self.frame.combobox_power.currentText()
            self.power_get(self._update_pwr_ui, pwr_elem_var)
            itf_send(uart_dev, pt.cli_proto_power_get())
        except Exception as e:
            #bflb_utils.printf(e)
            pass

    def _cmd_queue_duty_update(self, uart_dev):
        try:
            duty_elem_var = self.frame.combobox_txduty.currentText()
            self.duty_get(self._update_duty_ui, duty_elem_var)
            itf_send(uart_dev, pt.cli_proto_duty_get())
        except Exception as e:
            #bflb_utils.printf(e)
            pass

    def _cmd_queue_capcode_update(self, uart_dev):
        try:
            capcode_elem_var = self.frame.text_capcode.text()
            self.capcode_get(self._update_capcode_ui, capcode_elem_var)
            itf_send(uart_dev, pt.cli_proto_capcode_get())
        except Exception as e:
            #bflb_utils.printf(e)
            pass

    def _cmd_queue_mfgmode_update(self, uart_dev):
        try:
            mfgmode_elem_var = self.frame.combobox_mode.currentText()
            self.mfgmode_get(self._update_mfgmode_ui, mfgmode_elem_var)
            itf_send(uart_dev, pt.cli_proto_mfgmode_get())
        except Exception as e:
            #bflb_utils.printf(e)
            pass

    def _cmd_queue_add(self, func):
        if func is not None:
            self.cmd_queue.append(func)
            if self.cmd_queue_status == 0:
                self.cmd_queue_status = 1
                self._cmd_queue_start()

    def _cmd_queue_start(self):
        func = self.cmd_queue.pop(0)
        func()
        time.sleep(0.2)

    def on_boot(self, uart_dev):
        self._cmd_queue_add(self._cmd_queue_chan_update(uart_dev))
        self._cmd_queue_add(self._cmd_queue_pwr_update(uart_dev))
        self._cmd_queue_add(self._cmd_queue_duty_update(uart_dev))
        self._cmd_queue_add(self._cmd_queue_capcode_update(uart_dev))
        self._cmd_queue_add(self._cmd_queue_mfgmode_update(uart_dev))

    def timeout_oper_done(self):
        self._cur_oper_done()

    def is_done(self):
        return self._is_cur_oper_done()


class Bl60xMfgMisc(object):

    def __init__(self, observer):
        self._ch = '1(2412)'
        self._pwr = '17dbm'
        self._frm_len = '1946'
        self._frm_freq = '100'
        self._cap_code = '32'
        self._obs = observer

    """It runs at rx Thread"""

    def _channel_set(self, uart_dev, ch):
        self._ch = ch
        idx = self._ch.find('(')
        int_channel = int(self._ch[:idx])
        proto_frame = pt.cli_proto_channel_setting(int_channel)
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)

    def _power_set(self, uart_dev, pwr):
        self._pwr = pwr
        if self._pwr == 'Auto':
            proto_frame = pt.cli_proto_tx_power_setting('-1')
            bflb_utils.printf(proto_frame)
            itf_send(uart_dev, proto_frame)
        else:
            idx = self._pwr.find('dbm')
            int_pwr = int(self._pwr[:idx])
            proto_frame = pt.cli_proto_tx_power_setting(int_pwr)
            bflb_utils.printf(proto_frame)
            itf_send(uart_dev, proto_frame)

    def _offset_set(self, uart_dev, offset):
        if offset == "Disable":
            proto_frame = pt.cli_proto_power_offset_disable()
        else:
            proto_frame = pt.cli_proto_power_offset_enable()
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)

    def _duty_set(self, uart_dev, duty):
        self._duty = duty
        idx = self._duty.find('%')
        int_duty = int(self._duty[:idx])
        proto_frame = pt.cli_proto_tx_duty_setting(int_duty)
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)

    def _frm_len_set(self, uart_dev, frm_len):
        self._frm_len = frm_len
        int_frm_len = int(self._frm_len)
        proto_frame = pt.cli_proto_tx_len_setting(int_frm_len)
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)

    def _frm_freq_set(self, uart_dev, frm_freq):
        self._frm_freq = frm_freq
        int_frm_freq = int(self._frm_freq)
        proto_frame = pt.cli_proto_freq_setting(int_frm_freq)
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)

    def _cap_code_set(self, uart_dev, cap_code):
        self._cap_code = cap_code
        int_cap_code = int(self._cap_code)
        proto_frame = pt.cli_proto_capcode(int_cap_code)
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)

    def mfg_mode_set(self, uart_dev, mfg_mode):
        self._mfg_mode = mfg_mode
        int_mfg_mode = int(self._mfg_mode)
        proto_frame = pt.cli_proto_mfgmode(int_mfg_mode)
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)

    def _power_save(self, uart_dev, channel, pwr):
        self._pwr = pwr
        self._ch = channel
        if self._pwr == 'Auto':
            proto_frame = pt.cli_proto_save_power_setting('', '-1')
            bflb_utils.printf(proto_frame)
            itf_send(uart_dev, proto_frame)
        else:

            idc = self._ch.find('(')
            str_channel = int(self._ch[:idc])

            idx = self._pwr.find('dbm')
            int_pwr = int(self._pwr[:idx])
            proto_frame = pt.cli_proto_save_power_setting(str_channel, int_pwr)
            bflb_utils.printf(proto_frame)
            itf_send(uart_dev, proto_frame)

    def _power_read(self, uart_dev):
        proto_frame = pt.cli_proto_read_power_setting('-1')
        bflb_utils.printf(proto_frame)
        itf_send(uart_dev, proto_frame)

    def mfg_misc_save_in_falsh(self, uart_dev, channel, pwr):
        self._power_save(uart_dev, channel, pwr)
        time.sleep(0.01)

    def mfg_misc_read_from_falsh(self, uart_dev):
        self._power_read(uart_dev)
        time.sleep(0.01)

    def mfg_misc_set_ok(self, uart_dev, ch, pwr, offset, duty, frm_len, frm_freq, cap_code):
        self._offset_set(uart_dev, offset)
        time.sleep(0.01)
        #if self._ch != ch:
        self._channel_set(uart_dev, ch)
        time.sleep(0.01)
        #if self._pwr != pwr:
        self._power_set(uart_dev, pwr)
        time.sleep(0.01)
        #if self._duty != duty:
        self._duty_set(uart_dev, duty)
        time.sleep(0.01)
        #if self._frm_len != frm_len:
        self._frm_len_set(uart_dev, frm_len)
        time.sleep(0.01)
        #if self._frm_freq != frm_freq:
        self._frm_freq_set(uart_dev, frm_freq)
        time.sleep(0.01)
        #if self._cap_code != cap_code:
        if cap_code != "":
            self._cap_code_set(uart_dev, cap_code)
        time.sleep(0.01)

    def mfg_misc_get_ok(self, uart_dev):
        self._obs.on_boot(uart_dev)
