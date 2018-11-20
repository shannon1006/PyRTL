circuit Example : 
  module Example : 
    input clock : Clock
    input reset : UInt<1>
    wire tmp15 : UInt<1>
    wire tmp16 : UInt<1>
    wire tmp17 : UInt<1>
    wire tmp18 : UInt<1>
    wire tmp19 : UInt<1>
    wire tmp13 : UInt<1>
    wire tmp21 : UInt<1>
    wire tmp22 : UInt<1>
    wire tmp23 : UInt<1>
    wire tmp24 : UInt<1>
    wire tmp25 : UInt<1>
    wire tmp26 : UInt<1>
    wire tmp27 : UInt<1>
    wire tmp28 : UInt<1>
    wire tmp29 : UInt<1>
    wire tmp30 : UInt<1>
    wire tmp31 : UInt<2>
    wire tmp32 : UInt<3>
    node const_0_1 = UInt<1>(1)
    wire tmp12 : UInt<2>
    reg counter : UInt<3>, clock
    wire tmp2 : UInt<1>
    node const_1_0 = UInt<1>(0)
    wire tmp14 : UInt<1>
    wire tmp0 : UInt<2>
    wire tmp1 : UInt<3>
    wire tmp3 : UInt<1>
    wire tmp4 : UInt<1>
    node const_2_0 = UInt<1>(0)
    wire tmp5 : UInt<1>
    wire tmp6 : UInt<1>
    node const_3_0 = UInt<1>(0)
    wire tmp8 : UInt<1>
    wire tmp7 : UInt<1>
    wire tmp20 : UInt<1>
    node const_4_0 = UInt<1>(0)
    wire tmp9 : UInt<1>
    wire tmp10 : UInt<1>
    wire tmp11 : UInt<2>

    tmp11 <= bits(counter, 2, 1)
    tmp4 <= xor(tmp2, tmp3)
    tmp12 <= bits(tmp1, 2, 1)
    tmp8 <= or(tmp6, tmp7)
    tmp15 <= xor(tmp13, tmp14)
    tmp9 <= and(tmp3, const_4_0)
    tmp24 <= xor(tmp22, tmp23)
    tmp13 <= bits(tmp11, 0, 0)
    tmp5 <= xor(tmp4, const_2_0)
    tmp28 <= or(tmp26, tmp27)
    tmp23 <= bits(tmp12, 1, 1)
    tmp30 <= or(tmp28, tmp29)
    tmp6 <= and(tmp2, tmp3)
    tmp25 <= xor(tmp24, tmp21)
    tmp32 <= cat(tmp31, tmp5)
    tmp26 <= and(tmp22, tmp23)
    tmp2 <= bits(counter, 0, 0)
    tmp19 <= or(tmp17, tmp18)
    tmp18 <= and(tmp13, tmp10)
    counter <= mux(reset, UInt<3>(0), tmp32)
    tmp29 <= and(tmp23, tmp21)
    tmp20 <= and(tmp14, tmp10)
    tmp21 <= or(tmp19, tmp20)
    tmp31 <= cat(tmp25, tmp16)
    tmp0 <= bits(const_1_0, 0, 0)
    tmp16 <= xor(tmp15, tmp10)
    tmp7 <= and(tmp2, const_3_0)
    tmp27 <= and(tmp22, tmp21)
    tmp17 <= and(tmp13, tmp14)
    tmp3 <= bits(tmp1, 0, 0)
    tmp22 <= bits(tmp11, 1, 1)
    tmp10 <= or(tmp8, tmp9)
    tmp14 <= bits(tmp12, 0, 0)
    tmp1 <= cat(tmp0, const_0_1)
