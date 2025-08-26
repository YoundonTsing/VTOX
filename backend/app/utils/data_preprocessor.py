import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MotorDataPreprocessor:
    """电机数据预处理器：将原始传感器数据转换为匝间短路算法所需格式"""
    
    def __init__(self, pole_pairs=4, kt=1.2):
        """
        初始化预处理器
        :param pole_pairs: 电机极对数
        :param kt: 扭矩常数 (N·m/A)
        """
        self.pole_pairs = pole_pairs
        self.kt = kt
    
    def preprocess(self, file_path):
        """
        预处理CSV文件
        :param file_path: 原始CSV文件路径
        :return: 处理后的DataFrame
        """
        try:
            # 读取原始数据
            logger.info(f"开始读取CSV文件: {file_path}")
            df_raw = None
            read_exception = None
            
            # 尝试不同的编码
            for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1', 'iso-8859-1']:
                try:
                    logger.info(f"尝试使用 {encoding} 编码读取文件")
                    df_raw = pd.read_csv(file_path, encoding=encoding)
                    logger.info(f"成功使用 {encoding} 编码读取CSV文件")
                    break
                except Exception as e:
                    read_exception = e
                    logger.warning(f"使用 {encoding} 编码读取失败: {str(e)}")
                    continue
            
            if df_raw is None:
                # 如果所有编码都失败，尝试使用更多容错的参数
                try:
                    logger.info("尝试使用更宽松的解析参数读取文件")
                    df_raw = pd.read_csv(file_path, encoding='latin1', sep=None, engine='python', on_bad_lines='skip')
                    logger.info("成功使用宽松解析读取CSV文件")
                except Exception as e:
                    read_exception = e
                    logger.error(f"所有尝试读取CSV文件均失败: {str(e)}")
                    raise ValueError(f"无法读取CSV文件，请检查文件格式: {str(read_exception)}")
                    
            logger.info(f"读取原始数据，共{len(df_raw)}行")
            
            # 检查文件是否为空
            if df_raw.empty:
                raise ValueError("CSV文件为空")
                
            # 检查列名
            logger.info(f"原始列名: {df_raw.columns.tolist()}")
            
            # 尝试猜测列的含义
            self._guess_column_meanings(df_raw)
            
            # 直接检查是否是已处理的格式
            required_columns = ['timestamp', 'Ia', 'Ib', 'Ic', 'Vdc', 'Torque', 
                               'Speed', 'Iq_actual', 'Iq_ref', 'I2_ref', 'Eta_ref', 'Id_actual']
            
            # 计算匹配的列数
            existing_columns = [col for col in required_columns if col in df_raw.columns]
            
            # 如果已经有超过75%的所需列，可能是已处理过的数据
            if len(existing_columns) >= len(required_columns) * 0.75:
                logger.info("检测到文件已包含处理后格式的列，跳过规范化列名步骤")
                # 直接计算缺失值
                df_result = self._calculate_missing_values(df_raw)
                # 平滑处理
                df_result = self._smooth_data(df_result)
                logger.info(f"预处理完成（已处理格式），结果数据行数: {len(df_result)}")
                return df_result
                
            # 对于未处理过的数据，进行规范化列名
            logger.info(f"开始规范化列名")
            df_raw = self._normalize_column_names(df_raw)
            
            # 检查是否是已处理过的数据格式（规范化后）
            if all(col in df_raw.columns for col in ['ia', 'ib', 'ic', 'timestamp']):
                logger.info("规范化后检测到包含必要列，跳过时间戳生成")
                # 直接进入缺失值计算阶段
                df_result = self._calculate_missing_values(df_raw)
                df_result = self._smooth_data(df_result)
                logger.info(f"预处理完成（规范化后包含必要列），结果数据行数: {len(df_result)}")
                return df_result
                
            # 生成时间戳
            logger.info("生成时间戳")
            df_raw = self._generate_timestamps(df_raw)
            
            # 计算缺失值
            logger.info("计算缺失值")
            df_result = self._calculate_missing_values(df_raw)
            
            # 平滑处理
            logger.info("进行数据平滑处理")
            df_result = self._smooth_data(df_result)
            
            logger.info(f"预处理完成，结果数据行数: {len(df_result)}")
            return df_result
            
        except Exception as e:
            logger.error(f"数据预处理失败: {str(e)}")
            raise
    
    def _normalize_column_names(self, df):
        """规范化列名，适应不同格式的数据文件"""
        column_mapping = {
            # 时间列
            'Time[s]': 'time',
            'Time': 'time',
            'time': 'time',
            'timestamp': 'time',
            '时间': 'time',
            
            # 转速列
            'MotorRpm[Rpm]': 'rpm',
            'MotorRpm': 'rpm',
            'RPM': 'rpm',
            'Speed': 'rpm',
            'speed': 'rpm',
            '转速': 'rpm',
            
            # 电压列
            'BUS_500K_DBC23BusVoltage': 'vdc',
            'BusVoltage': 'vdc',
            'Voltage': 'vdc',
            'Vdc': 'vdc',
            'vdc': 'vdc',
            
            # 温度列
            'MotorTem': 'temp',
            'Temperature': 'temp',
            'Temp': 'temp',
            
            # 电流列
            'AphaseCurrent[A]': 'ia',
            'BPhaseCurrent[A]': 'ib',
            'CPhaseCurrent[A]': 'ic',
            'Ia': 'ia',
            'Ib': 'ib',
            'Ic': 'ic',
            
            # 振动数据列
            '加速度X': 'acc_x',
            '加速度Y': 'acc_y',
            '加速度Z': 'acc_z',
            'AccX': 'acc_x',
            'AccY': 'acc_y',
            'AccZ': 'acc_z',
            'AccelerationX': 'acc_x',
            'AccelerationY': 'acc_y',
            'AccelerationZ': 'acc_z',
            'Vibration': 'vibration',
            '振动': 'vibration',
            
            # 负载列
            '负载': 'load',
            'Load': 'load'
        }
        
        # 创建新的列名映射
        new_columns = {}
        for col in df.columns:
            col_str = str(col).strip()  # 确保列名是字符串并去除空格
            mapped = False
            
            # 特殊处理：保留timestamp列，不要将其映射为time
            if col_str.lower() == 'timestamp':
                new_columns[col] = col_str
                mapped = True
                continue
                
            # 尝试查找精确匹配
            if col_str.lower() in [key.lower() for key in column_mapping.keys()]:
                # 找到精确匹配的键
                for key, value in column_mapping.items():
                    if col_str.lower() == key.lower():
                        new_columns[col] = value
                        mapped = True
                        break
            
            # 如果没有找到精确匹配，尝试部分匹配
            if not mapped:
                for key, value in column_mapping.items():
                    # 检查列名是否包含关键词（如'time', 'rpm'等）
                    if key.lower() in col_str.lower() or value in col_str.lower():
                        new_columns[col] = value
                        mapped = True
                        break
            
            # 如果仍然没有找到映射，保留原列名
            if not mapped:
                new_columns[col] = col
        
        # 重命名列
        df = df.rename(columns=new_columns)
        
        # 记录映射结果
        logger.info(f"列名映射结果: {new_columns}")
        logger.info(f"规范化后的列: {df.columns.tolist()}")
        
        # 检查是否有振动数据列
        vibration_columns = [col for col in df.columns if any(s in col for s in ['acc_', 'vibration'])]
        
        # 如果有振动数据列，说明这是轴承数据，使用不同的必要列检查
        if vibration_columns:
            logger.info(f"检测到振动数据列: {vibration_columns}，按轴承数据处理")
            # 轴承数据只需要时间列和至少一个振动数据列
            required_columns = ['time']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                # 尝试自动处理一些特殊情况
                if 'time' in missing_columns and 'timestamp' in df.columns:
                    df['time'] = df['timestamp']
                    missing_columns.remove('time')
                elif 'time' in missing_columns and 'Time[s]' in df.columns:
                    df['time'] = df['Time[s]']
                    missing_columns.remove('time')
                
                # 如果仍然缺少必要列，则报错
                if missing_columns:
                    raise ValueError(f"缺少必要的列: {', '.join(missing_columns)}")
            
            # 如果没有振动数据列，使用第一个非时间列作为振动数据
            if not vibration_columns and len(df.columns) > 1:
                non_time_cols = [col for col in df.columns if col != 'time']
                vibration_col = non_time_cols[0]
                df['vibration'] = df[vibration_col]
                logger.info(f"未找到明确的振动数据列，使用 {vibration_col} 作为振动数据")
            
            # 确保有rpm列，如果没有则添加默认值
            if 'rpm' not in df.columns:
                df['rpm'] = 1500.0  # 使用默认转速值
                logger.warning("使用默认转速值 1500RPM 填充缺失的rpm列")
            
            # 为了兼容性，添加ia, ib, ic列（使用振动数据填充）
            if 'ia' not in df.columns:
                if vibration_columns:
                    df['ia'] = df[vibration_columns[0]]
                else:
                    df['ia'] = df['vibration']
                logger.warning("使用振动数据填充缺失的ia列")
            
            if 'ib' not in df.columns:
                if len(vibration_columns) > 1:
                    df['ib'] = df[vibration_columns[1]]
                else:
                    df['ib'] = df['ia']
                logger.warning("使用振动数据填充缺失的ib列")
            
            if 'ic' not in df.columns:
                if len(vibration_columns) > 2:
                    df['ic'] = df[vibration_columns[2]]
                else:
                    df['ic'] = df['ia']
                logger.warning("使用振动数据填充缺失的ic列")
            
            # 添加vdc列
            if 'vdc' not in df.columns:
                df['vdc'] = 380.0  # 使用默认电压值
                logger.warning("使用默认电压值 380V 填充缺失的vdc列")
            
            return df
        
        # 如果没有振动数据列，按照电机数据处理
        required_columns = ['time', 'rpm', 'vdc', 'ia', 'ib', 'ic']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            # 尝试自动处理一些特殊情况
            if 'time' in missing_columns and 'timestamp' in df.columns:
                df['time'] = df['timestamp']
                missing_columns.remove('time')
            elif 'time' in missing_columns and 'Time[s]' in df.columns:
                df['time'] = df['Time[s]']
                missing_columns.remove('time')
            
            # 自动生成可能缺失的列
            if 'vdc' in missing_columns:
                df['vdc'] = 380.0  # 使用默认电压值
                logger.warning("使用默认电压值 380V 填充缺失的vdc列")
                missing_columns.remove('vdc')
            
            if 'rpm' in missing_columns:
                df['rpm'] = 1000.0  # 使用默认转速值
                logger.warning("使用默认转速值 1000RPM 填充缺失的rpm列")
                missing_columns.remove('rpm')
            
            # 如果仍然缺少必要列，则报错
            if missing_columns:
                raise ValueError(f"缺少必要的列: {', '.join(missing_columns)}")
            
        return df
    
    def _generate_timestamps(self, df):
        """生成ISO 8601格式的时间戳"""
        # 如果time列的值已经是ISO 8601格式的时间戳，直接使用该值
        # 检测第一个值是否看起来像ISO 8601时间戳
        if 'time' in df.columns and len(df['time']) > 0:
            first_value = str(df['time'].iloc[0])
            if 'T' in first_value and ('Z' in first_value or '+' in first_value):
                logger.info("时间列已经是ISO 8601格式，直接使用")
                # 确保timestamp列存在
                if 'timestamp' not in df.columns:
                    df['timestamp'] = df['time']
                return df
            
        # 使用当前UTC时间作为基准
        base_time = datetime.utcnow()
        
        try:
            # 生成时间戳
            df['timestamp'] = df['time'].apply(
                lambda t: (base_time + timedelta(seconds=float(t))).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            )
        except ValueError as e:
            logger.warning(f"时间戳转换失败: {str(e)}，尝试直接使用time列值")
            # 如果转换失败，尝试直接使用time列的值
            df['timestamp'] = df['time']
        
        return df
    
    def _abc_to_dq(self, ia, ib, ic, rpm, time_elapsed):
        """
        将三相电流转换为d-q轴电流
        :param ia, ib, ic: 三相电流
        :param rpm: 电机转速(RPM)
        :param time_elapsed: 累积时间(s)
        :return: id, iq
        """
        # Clarke变换 (3相 → α-β)
        i_alpha = (2*ia - ib - ic) / 3
        i_beta = (ib - ic) / np.sqrt(3)
        
        # 计算电角度 (θ = ωt = 2π*f*t)
        # 电频率(Hz) = (rpm * pole_pairs) / 60
        freq = (rpm * self.pole_pairs) / 60
        theta = 2 * np.pi * freq * time_elapsed
        
        # Park变换 (α-β → dq)
        id = i_alpha * np.cos(theta) + i_beta * np.sin(theta)
        iq = -i_alpha * np.sin(theta) + i_beta * np.cos(theta)
        
        return id, iq
    
    def _estimate_torque(self, iq):
        """
        基于q轴电流估算扭矩
        :param iq: q轴电流
        :return: 估算扭矩值
        """
        return iq * self.kt
    
    def _calculate_missing_values(self, df):
        """计算缺失的值"""
        # 检查数据是否已经是处理过的格式（包含了所有需要的列）
        required_columns = ['timestamp', 'Ia', 'Ib', 'Ic', 'Vdc', 'Torque', 
                            'Speed', 'Iq_actual', 'Iq_ref', 'I2_ref', 'Eta_ref', 'Id_actual']
        
        # 计算匹配的列数
        existing_columns = [col for col in required_columns if col in df.columns]
        
        # 如果已经有超过75%的所需列，可能是已处理过的数据
        if len(existing_columns) >= len(required_columns) * 0.75:
            logger.info(f"检测到文件已包含处理后格式的列: {existing_columns}")
            
            # 创建结果DataFrame，保持原始列顺序
            df_result = pd.DataFrame()
            
            # 首先复制所有现有列
            for col in df.columns:
                df_result[col] = df[col].copy()
            
            # 标准化列名（小写转大写）
            col_mapping = {}
            for col in df_result.columns:
                # 检查是否是小写版本的必需列
                lowercase_col = col.lower()
                for req_col in required_columns:
                    if lowercase_col == req_col.lower():
                        col_mapping[col] = req_col
                        break
            
            # 重命名列
            if col_mapping:
                logger.info(f"标准化列名: {col_mapping}")
                df_result.rename(columns=col_mapping, inplace=True)
                
            # 检查并添加缺失的必需列
            missing_columns = [col for col in required_columns if col not in df_result.columns]
            for col in missing_columns:
                # 根据缺失的列创建默认值
                if col == 'Iq_ref' and 'Iq_actual' in df_result.columns:
                    df_result[col] = df_result['Iq_actual'] * 0.98
                elif col == 'I2_ref':
                    df_result[col] = 0.02  # 默认负序电流参考值
                elif col == 'Eta_ref':
                    df_result[col] = 0.93  # 默认效率参考值
                else:
                    df_result[col] = 0  # 其他列使用0填充
                
                logger.info(f"添加缺失的列: {col}")
            
            # 确保所有列都在结果DataFrame中，并按照标准顺序排列
            # 先确保所有必需列存在
            for col in required_columns:
                if col not in df_result.columns:
                    df_result[col] = 0
            
            # 重新排列列顺序
            result_columns = required_columns + [col for col in df_result.columns if col not in required_columns]
            df_result = df_result[result_columns]
            
            logger.info(f"处理完成，共{len(df_result)}行数据，列: {df_result.columns.tolist()}")
            return df_result
            
        # 否则，计算缺失的值（原始格式数据）
        logger.info("原始格式数据，需要计算缺失值")
        
        # 创建结果DataFrame
        df_result = pd.DataFrame(columns=required_columns)
        
        # 确保我们有一个时间列
        if 'time' not in df.columns:
            df['time'] = range(len(df))  # 创建一个序号作为时间
            logger.warning("找不到时间列，使用序号作为时间")
        
        # 检查time列是否是ISO 8601格式
        is_iso_format = False
        if 'time' in df.columns and len(df['time']) > 0:
            first_value = str(df['time'].iloc[0])
            if 'T' in first_value and ('Z' in first_value or '+' in first_value):
                logger.info("时间列是ISO 8601格式，使用序号作为累积时间")
                is_iso_format = True
        
        cumulative_time = 0  # 时间累积量
        
        # 如果不是ISO格式，尝试用float转换；如果是，使用序号
        if not is_iso_format:
            try:
                last_time = float(df.iloc[0]['time']) if 'time' in df.columns else 0
            except (ValueError, TypeError):
                logger.warning("无法将time列转换为float，使用序号")
                last_time = 0
        else:
            last_time = 0
        
        # 逐行处理数据
        for idx, row in df.iterrows():
            try:
                # 计算时间增量和累积时间
                if is_iso_format:
                    # 如果是ISO 8601格式，使用序号替代实际时间值
                    current_time = idx
                    delta_t = 1  # 固定步长
                else:
                    # 尝试将time列转换为float
                    try:
                        current_time = float(row['time']) if 'time' in row and pd.notna(row['time']) else idx
                    except (ValueError, TypeError):
                        # 如果转换失败，使用行索引
                        current_time = idx
                        logger.debug(f"行 {idx}: 无法转换time列，使用索引")
                
                # 只有当time是数值时才计算增量
                if isinstance(current_time, (int, float)) and isinstance(last_time, (int, float)):
                    delta_t = current_time - last_time
                    cumulative_time += max(delta_t, 0)  # 避免负时间
                    last_time = current_time
                else:
                    # 使用固定增量
                    cumulative_time += 1
                
                # 提取基础值
                ia = float(row['ia']) if 'ia' in row and pd.notna(row['ia']) else 0
                ib = float(row['ib']) if 'ib' in row and pd.notna(row['ib']) else 0
                ic = float(row['ic']) if 'ic' in row and pd.notna(row['ic']) else 0
                
                # 如果rpm列不存在，使用默认值
                rpm = float(row['rpm']) if 'rpm' in row and pd.notna(row['rpm']) else 1000.0
                
                # 如果vdc列不存在，使用默认值
                vdc = float(row['vdc']) if 'vdc' in row and pd.notna(row['vdc']) else 380.0
                
                # 计算d-q轴电流
                id_actual, iq_actual = self._abc_to_dq(ia, ib, ic, rpm, cumulative_time)
                
                # 估算扭矩
                torque = self._estimate_torque(iq_actual)
                
                # 设置默认参考值
                iq_ref = max(iq_actual * 0.98, 0)  # 略小于实际值
                i2_ref = 0.02  # 固定负序电流参考值
                eta_ref = 0.93  # 固定效率参考值
                
                # 生成时间戳（如果没有）
                timestamp = row.get('timestamp', pd.Timestamp.now().isoformat())
                
                # 添加到结果集
                df_result.loc[idx] = [
                    timestamp,
                    ia,
                    ib,
                    ic,
                    vdc,
                    torque,
                    rpm,
                    iq_actual,
                    iq_ref,
                    i2_ref,
                    eta_ref,
                    id_actual
                ]
                
                # 如果是第一行，记录处理结果
                if idx == 0:
                    logger.debug(f"第1行处理成功: ia={ia}, ib={ib}, ic={ic}, id={id_actual}, iq={iq_actual}")
                
            except Exception as e:
                logger.error(f"处理第{idx}行时出错: {str(e)}")
                # 继续处理下一行
                continue
        
        # 如果结果为空，抛出错误
        if len(df_result) == 0:
            raise ValueError("无法处理数据，请检查CSV文件格式")
        
        logger.info(f"处理完成，共生成{len(df_result)}行数据")
        return df_result
    
    def _smooth_data(self, df, window_size=5):
        """平滑处理数据"""
        # 平滑d-q轴电流
        if len(df) >= window_size:
            df['Iq_actual'] = df['Iq_actual'].rolling(window=window_size, center=True).mean().fillna(df['Iq_actual'])
            df['Id_actual'] = df['Id_actual'].rolling(window=window_size, center=True).mean().fillna(df['Id_actual'])
        
        return df
        
    def _guess_column_meanings(self, df):
        """
        尝试猜测乱码或非标准列名的含义
        :param df: 原始DataFrame
        """
        try:
            # 如果列名可能是乱码，尝试从数据内容和列位置推断列的含义
            has_encoding_issue = any(not col.isascii() for col in df.columns)
            
            if has_encoding_issue:
                logger.info("检测到列名可能存在编码问题，尝试通过位置和数据特征推断列的含义")
                
                # 根据列的位置进行初步猜测
                if len(df.columns) >= 2:  # 至少有两列
                    # 第一列通常是时间
                    time_col = df.columns[0]
                    # 如果第一列数据是升序排列的数字，很可能是时间列
                    if pd.api.types.is_numeric_dtype(df[time_col]):
                        first_values = df[time_col].iloc[:10].tolist()
                        is_increasing = all(first_values[i] <= first_values[i+1] for i in range(len(first_values)-1))
                        if is_increasing:
                            logger.info(f"猜测列 '{time_col}' 是时间列")
                            df.rename(columns={time_col: 'time'}, inplace=True)
                
                # 检查数据特征来猜测振动数据列
                for col in df.columns:
                    # 振动数据通常是围绕0波动的值
                    if pd.api.types.is_numeric_dtype(df[col]) and col != 'time':
                        mean = df[col].mean()
                        std = df[col].std()
                        # 如果均值接近0且标准差显著，可能是振动数据
                        if abs(mean) < 5 * std:
                            logger.info(f"猜测列 '{col}' 是振动/加速度数据")
                            # 找到第一个振动列作为acc_x
                            if 'acc_x' not in df.columns:
                                df.rename(columns={col: 'acc_x'}, inplace=True)
                            # 第二个作为acc_y
                            elif 'acc_y' not in df.columns:
                                df.rename(columns={col: 'acc_y'}, inplace=True)
                            # 第三个作为acc_z
                            elif 'acc_z' not in df.columns:
                                df.rename(columns={col: 'acc_z'}, inplace=True)
                
                # 转速列通常是比较稳定的值且在几百到几千RPM
                for col in df.columns:
                    if col not in ['time', 'acc_x', 'acc_y', 'acc_z'] and pd.api.types.is_numeric_dtype(df[col]):
                        mean = df[col].mean()
                        std = df[col].std() / max(1, abs(mean))  # 相对标准差
                        # 如果值比较稳定且在合理范围内
                        if std < 0.1 and 100 < mean < 10000:
                            logger.info(f"猜测列 '{col}' 是转速数据")
                            df.rename(columns={col: 'rpm'}, inplace=True)
                            break
                
                # 负载列通常是0-100之间的值
                for col in df.columns:
                    if col not in ['time', 'acc_x', 'acc_y', 'acc_z', 'rpm'] and pd.api.types.is_numeric_dtype(df[col]):
                        min_val = df[col].min()
                        max_val = df[col].max()
                        # 如果范围在0-100左右
                        if 0 <= min_val and max_val <= 110:
                            logger.info(f"猜测列 '{col}' 是负载数据")
                            df.rename(columns={col: 'load'}, inplace=True)
                            break
                
                logger.info(f"列名猜测后: {df.columns.tolist()}")
        except Exception as e:
            logger.warning(f"猜测列名含义时出错: {str(e)}")
            # 继续处理，不终止


def preprocess_motor_data(file_path, output_path=None):
    """
    预处理电机数据文件
    :param file_path: 输入文件路径
    :param output_path: 输出文件路径(可选)
    :return: 处理后的DataFrame
    """
    preprocessor = MotorDataPreprocessor()
    df_processed = preprocessor.preprocess(file_path)
    
    # 如果指定了输出路径，保存处理后的数据
    if output_path:
        df_processed.to_csv(output_path, index=False)
        logger.info(f"处理后的数据已保存到: {output_path}")
    
    return df_processed 