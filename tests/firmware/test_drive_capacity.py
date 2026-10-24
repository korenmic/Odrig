import pathlib
import subprocess
import tempfile
import unittest
from . import FIRMWARE


class DriveCapacity(unittest.TestCase):
    def test_native_fat_capacity_uses_64_bits_and_propagates_read_errors(self):
        source = (FIRMWARE / 'usb_host_msc/src/msc_host_vfs.c').read_text()
        function = source[source.index('esp_err_t msc_host_vfs_space('):]
        program = '''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#define FF_MAX_SS 4096
#define FF_MIN_SS 512
#define FR_OK 0
#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_ERR_INVALID_ARG -2
typedef int esp_err_t;
typedef uint32_t DWORD;
typedef struct {uint32_t ssize,csize,n_fatent;} FATFS;
typedef struct {char *drive;} *msc_host_vfs_handle_t;
static FATFS volume = {4096, 128, 131074};
static int broken = 0;
static int f_getfree(char *drive,DWORD *free,FATFS **fs) { (void)drive; *free=65536; *fs=&volume; return broken; }
''' + function + '''
int main(void) {
    struct {char *drive;} handle = {"0:"};
    uint64_t free=0,total=0;
    int ok=msc_host_vfs_space((msc_host_vfs_handle_t)&handle,&free,&total);
    printf("%d %llu %llu\\n",ok,(unsigned long long)free,(unsigned long long)total);
    broken=1;
    printf("%d\\n",msc_host_vfs_space((msc_host_vfs_handle_t)&handle,&free,&total));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as work:
            path = pathlib.Path(work, 'capacity')
            subprocess.run(['cc','-x','c','-std=c99','-Wall','-Wextra','-Werror','-o',str(path),'-'],input=program,text=True,capture_output=True,check=True)
            output = subprocess.check_output([str(path)],text=True)
        self.assertEqual(output, '0 34359738368 68719476736\n-1\n')
