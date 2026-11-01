const os = require('node:os');

const originalUserInfo = os.userInfo.bind(os);
os.userInfo = (options) => {
  try {
    return originalUserInfo(options);
  } catch {
    return {
      username: process.env.USERNAME || 'user',
      uid: -1,
      gid: -1,
      shell: process.env.ComSpec || 'cmd.exe',
      homedir: process.env.USERPROFILE || process.cwd(),
    };
  }
};

require('@capacitor/assets/bin/capacitor-assets');
