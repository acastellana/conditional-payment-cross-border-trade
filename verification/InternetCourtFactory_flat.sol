// SPDX-License-Identifier: MIT
pragma solidity >=0.4.16 >=0.6.2 ^0.8.20;

// node_modules/@openzeppelin/contracts/utils/Context.sol

// OpenZeppelin Contracts (last updated v5.0.1) (utils/Context.sol)

/**
 * @dev Provides information about the current execution context, including the
 * sender of the transaction and its data. While these are generally available
 * via msg.sender and msg.data, they should not be accessed in such a direct
 * manner, since when dealing with meta-transactions the account sending and
 * paying for execution may not be the actual sender (as far as an application
 * is concerned).
 *
 * This contract is only required for intermediate, library-like contracts.
 */
abstract contract Context {
    function _msgSender() internal view virtual returns (address) {
        return msg.sender;
    }

    function _msgData() internal view virtual returns (bytes calldata) {
        return msg.data;
    }

    function _contextSuffixLength() internal view virtual returns (uint256) {
        return 0;
    }
}

// node_modules/@openzeppelin/contracts/utils/introspection/IERC165.sol

// OpenZeppelin Contracts (last updated v5.4.0) (utils/introspection/IERC165.sol)

/**
 * @dev Interface of the ERC-165 standard, as defined in the
 * https://eips.ethereum.org/EIPS/eip-165[ERC].
 *
 * Implementers can declare support of contract interfaces, which can then be
 * queried by others ({ERC165Checker}).
 *
 * For an implementation, see {ERC165}.
 */
interface IERC165 {
    /**
     * @dev Returns true if this contract implements the interface defined by
     * `interfaceId`. See the corresponding
     * https://eips.ethereum.org/EIPS/eip-165#how-interfaces-are-identified[ERC section]
     * to learn more about how these ids are created.
     *
     * This function call must use less than 30 000 gas.
     */
    function supportsInterface(bytes4 interfaceId) external view returns (bool);
}

// node_modules/@openzeppelin/contracts/token/ERC20/IERC20.sol

// OpenZeppelin Contracts (last updated v5.4.0) (token/ERC20/IERC20.sol)

/**
 * @dev Interface of the ERC-20 standard as defined in the ERC.
 */
interface IERC20 {
    /**
     * @dev Emitted when `value` tokens are moved from one account (`from`) to
     * another (`to`).
     *
     * Note that `value` may be zero.
     */
    event Transfer(address indexed from, address indexed to, uint256 value);

    /**
     * @dev Emitted when the allowance of a `spender` for an `owner` is set by
     * a call to {approve}. `value` is the new allowance.
     */
    event Approval(address indexed owner, address indexed spender, uint256 value);

    /**
     * @dev Returns the value of tokens in existence.
     */
    function totalSupply() external view returns (uint256);

    /**
     * @dev Returns the value of tokens owned by `account`.
     */
    function balanceOf(address account) external view returns (uint256);

    /**
     * @dev Moves a `value` amount of tokens from the caller's account to `to`.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transfer(address to, uint256 value) external returns (bool);

    /**
     * @dev Returns the remaining number of tokens that `spender` will be
     * allowed to spend on behalf of `owner` through {transferFrom}. This is
     * zero by default.
     *
     * This value changes when {approve} or {transferFrom} are called.
     */
    function allowance(address owner, address spender) external view returns (uint256);

    /**
     * @dev Sets a `value` amount of tokens as the allowance of `spender` over the
     * caller's tokens.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * IMPORTANT: Beware that changing an allowance with this method brings the risk
     * that someone may use both the old and the new allowance by unfortunate
     * transaction ordering. One possible solution to mitigate this race
     * condition is to first reduce the spender's allowance to 0 and set the
     * desired value afterwards:
     * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
     *
     * Emits an {Approval} event.
     */
    function approve(address spender, uint256 value) external returns (bool);

    /**
     * @dev Moves a `value` amount of tokens from `from` to `to` using the
     * allowance mechanism. `value` is then deducted from the caller's
     * allowance.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transferFrom(address from, address to, uint256 value) external returns (bool);
}

// contracts/bridge/IGenLayerBridgeReceiver.sol

interface IGenLayerBridgeReceiver {
    function processBridgeMessage(
        uint32 srcChainId,
        address srcSender,
        bytes calldata message
    ) external;
}

// contracts/IResolutionTarget.sol

/**
 * @title IResolutionTarget
 * @notice Minimal interface that any InternetCourt case contract must implement
 *         to receive a verdict delivered from GenLayer via the bridge.
 *
 *         Implemented by:
 *           - Agreement.sol     (agent disputes)
 *           - TradeFxSettlement (trade finance disputes)
 *           - Any future case type registered via InternetCourtFactory.registerCase()
 */
interface IResolutionTarget {
    /**
     * @notice Deliver a verdict to the case contract.
     *         Called by InternetCourtFactory after the bridge delivers a verdict from GenLayer.
     * @param verdict  Oracle-type-specific uint8 verdict code.
     *                 Agent disputes:  0=UNDETERMINED, 1=TRUE, 2=FALSE
     *                 Trade finance:   1=TIMELY, 2=LATE, 3=UNDETERMINED
     * @param reasoning  Human-readable explanation from the AI jury.
     */
    function setResolution(uint8 verdict, string calldata reasoning) external;

    /**
     * @notice Oracle type identifier. The relay uses this to look up which
     *         GenLayer oracle to deploy and how to decode getOracleArgs().
     * @return  keccak256 of a versioned type string, e.g.
     *          keccak256("AGENT_DISPUTE_V1") or keccak256("TRADE_FINANCE_V1")
     */
    function getOracleType() external view returns (bytes32);

    /**
     * @notice ABI-encoded constructor arguments for the oracle contract.
     *         The relay decodes these according to the oracle type and passes
     *         them to glClient.deployContract(). Encoding schema is defined
     *         per oracle type in the relay's ORACLE_REGISTRY.
     */
    function getOracleArgs() external view returns (bytes memory);
}

// node_modules/@openzeppelin/contracts/interfaces/IERC165.sol

// OpenZeppelin Contracts (last updated v5.4.0) (interfaces/IERC165.sol)

// node_modules/@openzeppelin/contracts/interfaces/IERC20.sol

// OpenZeppelin Contracts (last updated v5.4.0) (interfaces/IERC20.sol)

// node_modules/@openzeppelin/contracts/access/Ownable.sol

// OpenZeppelin Contracts (last updated v5.0.0) (access/Ownable.sol)

/**
 * @dev Contract module which provides a basic access control mechanism, where
 * there is an account (an owner) that can be granted exclusive access to
 * specific functions.
 *
 * The initial owner is set to the address provided by the deployer. This can
 * later be changed with {transferOwnership}.
 *
 * This module is used through inheritance. It will make available the modifier
 * `onlyOwner`, which can be applied to your functions to restrict their use to
 * the owner.
 */
abstract contract Ownable is Context {
    address private _owner;

    /**
     * @dev The caller account is not authorized to perform an operation.
     */
    error OwnableUnauthorizedAccount(address account);

    /**
     * @dev The owner is not a valid owner account. (eg. `address(0)`)
     */
    error OwnableInvalidOwner(address owner);

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    /**
     * @dev Initializes the contract setting the address provided by the deployer as the initial owner.
     */
    constructor(address initialOwner) {
        if (initialOwner == address(0)) {
            revert OwnableInvalidOwner(address(0));
        }
        _transferOwnership(initialOwner);
    }

    /**
     * @dev Throws if called by any account other than the owner.
     */
    modifier onlyOwner() {
        _checkOwner();
        _;
    }

    /**
     * @dev Returns the address of the current owner.
     */
    function owner() public view virtual returns (address) {
        return _owner;
    }

    /**
     * @dev Throws if the sender is not the owner.
     */
    function _checkOwner() internal view virtual {
        if (owner() != _msgSender()) {
            revert OwnableUnauthorizedAccount(_msgSender());
        }
    }

    /**
     * @dev Leaves the contract without owner. It will not be possible to call
     * `onlyOwner` functions. Can only be called by the current owner.
     *
     * NOTE: Renouncing ownership will leave the contract without an owner,
     * thereby disabling any functionality that is only available to the owner.
     */
    function renounceOwnership() public virtual onlyOwner {
        _transferOwnership(address(0));
    }

    /**
     * @dev Transfers ownership of the contract to a new account (`newOwner`).
     * Can only be called by the current owner.
     */
    function transferOwnership(address newOwner) public virtual onlyOwner {
        if (newOwner == address(0)) {
            revert OwnableInvalidOwner(address(0));
        }
        _transferOwnership(newOwner);
    }

    /**
     * @dev Transfers ownership of the contract to a new account (`newOwner`).
     * Internal function without access restriction.
     */
    function _transferOwnership(address newOwner) internal virtual {
        address oldOwner = _owner;
        _owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}

// node_modules/@openzeppelin/contracts/interfaces/IERC1363.sol

// OpenZeppelin Contracts (last updated v5.4.0) (interfaces/IERC1363.sol)

/**
 * @title IERC1363
 * @dev Interface of the ERC-1363 standard as defined in the https://eips.ethereum.org/EIPS/eip-1363[ERC-1363].
 *
 * Defines an extension interface for ERC-20 tokens that supports executing code on a recipient contract
 * after `transfer` or `transferFrom`, or code on a spender contract after `approve`, in a single transaction.
 */
interface IERC1363 is IERC20, IERC165 {
    /*
     * Note: the ERC-165 identifier for this interface is 0xb0202a11.
     * 0xb0202a11 ===
     *   bytes4(keccak256('transferAndCall(address,uint256)')) ^
     *   bytes4(keccak256('transferAndCall(address,uint256,bytes)')) ^
     *   bytes4(keccak256('transferFromAndCall(address,address,uint256)')) ^
     *   bytes4(keccak256('transferFromAndCall(address,address,uint256,bytes)')) ^
     *   bytes4(keccak256('approveAndCall(address,uint256)')) ^
     *   bytes4(keccak256('approveAndCall(address,uint256,bytes)'))
     */

    /**
     * @dev Moves a `value` amount of tokens from the caller's account to `to`
     * and then calls {IERC1363Receiver-onTransferReceived} on `to`.
     * @param to The address which you want to transfer to.
     * @param value The amount of tokens to be transferred.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function transferAndCall(address to, uint256 value) external returns (bool);

    /**
     * @dev Moves a `value` amount of tokens from the caller's account to `to`
     * and then calls {IERC1363Receiver-onTransferReceived} on `to`.
     * @param to The address which you want to transfer to.
     * @param value The amount of tokens to be transferred.
     * @param data Additional data with no specified format, sent in call to `to`.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function transferAndCall(address to, uint256 value, bytes calldata data) external returns (bool);

    /**
     * @dev Moves a `value` amount of tokens from `from` to `to` using the allowance mechanism
     * and then calls {IERC1363Receiver-onTransferReceived} on `to`.
     * @param from The address which you want to send tokens from.
     * @param to The address which you want to transfer to.
     * @param value The amount of tokens to be transferred.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function transferFromAndCall(address from, address to, uint256 value) external returns (bool);

    /**
     * @dev Moves a `value` amount of tokens from `from` to `to` using the allowance mechanism
     * and then calls {IERC1363Receiver-onTransferReceived} on `to`.
     * @param from The address which you want to send tokens from.
     * @param to The address which you want to transfer to.
     * @param value The amount of tokens to be transferred.
     * @param data Additional data with no specified format, sent in call to `to`.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function transferFromAndCall(address from, address to, uint256 value, bytes calldata data) external returns (bool);

    /**
     * @dev Sets a `value` amount of tokens as the allowance of `spender` over the
     * caller's tokens and then calls {IERC1363Spender-onApprovalReceived} on `spender`.
     * @param spender The address which will spend the funds.
     * @param value The amount of tokens to be spent.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function approveAndCall(address spender, uint256 value) external returns (bool);

    /**
     * @dev Sets a `value` amount of tokens as the allowance of `spender` over the
     * caller's tokens and then calls {IERC1363Spender-onApprovalReceived} on `spender`.
     * @param spender The address which will spend the funds.
     * @param value The amount of tokens to be spent.
     * @param data Additional data with no specified format, sent in call to `spender`.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function approveAndCall(address spender, uint256 value, bytes calldata data) external returns (bool);
}

// node_modules/@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol

// OpenZeppelin Contracts (last updated v5.3.0) (token/ERC20/utils/SafeERC20.sol)

/**
 * @title SafeERC20
 * @dev Wrappers around ERC-20 operations that throw on failure (when the token
 * contract returns false). Tokens that return no value (and instead revert or
 * throw on failure) are also supported, non-reverting calls are assumed to be
 * successful.
 * To use this library you can add a `using SafeERC20 for IERC20;` statement to your contract,
 * which allows you to call the safe operations as `token.safeTransfer(...)`, etc.
 */
library SafeERC20 {
    /**
     * @dev An operation with an ERC-20 token failed.
     */
    error SafeERC20FailedOperation(address token);

    /**
     * @dev Indicates a failed `decreaseAllowance` request.
     */
    error SafeERC20FailedDecreaseAllowance(address spender, uint256 currentAllowance, uint256 requestedDecrease);

    /**
     * @dev Transfer `value` amount of `token` from the calling contract to `to`. If `token` returns no value,
     * non-reverting calls are assumed to be successful.
     */
    function safeTransfer(IERC20 token, address to, uint256 value) internal {
        _callOptionalReturn(token, abi.encodeCall(token.transfer, (to, value)));
    }

    /**
     * @dev Transfer `value` amount of `token` from `from` to `to`, spending the approval given by `from` to the
     * calling contract. If `token` returns no value, non-reverting calls are assumed to be successful.
     */
    function safeTransferFrom(IERC20 token, address from, address to, uint256 value) internal {
        _callOptionalReturn(token, abi.encodeCall(token.transferFrom, (from, to, value)));
    }

    /**
     * @dev Variant of {safeTransfer} that returns a bool instead of reverting if the operation is not successful.
     */
    function trySafeTransfer(IERC20 token, address to, uint256 value) internal returns (bool) {
        return _callOptionalReturnBool(token, abi.encodeCall(token.transfer, (to, value)));
    }

    /**
     * @dev Variant of {safeTransferFrom} that returns a bool instead of reverting if the operation is not successful.
     */
    function trySafeTransferFrom(IERC20 token, address from, address to, uint256 value) internal returns (bool) {
        return _callOptionalReturnBool(token, abi.encodeCall(token.transferFrom, (from, to, value)));
    }

    /**
     * @dev Increase the calling contract's allowance toward `spender` by `value`. If `token` returns no value,
     * non-reverting calls are assumed to be successful.
     *
     * IMPORTANT: If the token implements ERC-7674 (ERC-20 with temporary allowance), and if the "client"
     * smart contract uses ERC-7674 to set temporary allowances, then the "client" smart contract should avoid using
     * this function. Performing a {safeIncreaseAllowance} or {safeDecreaseAllowance} operation on a token contract
     * that has a non-zero temporary allowance (for that particular owner-spender) will result in unexpected behavior.
     */
    function safeIncreaseAllowance(IERC20 token, address spender, uint256 value) internal {
        uint256 oldAllowance = token.allowance(address(this), spender);
        forceApprove(token, spender, oldAllowance + value);
    }

    /**
     * @dev Decrease the calling contract's allowance toward `spender` by `requestedDecrease`. If `token` returns no
     * value, non-reverting calls are assumed to be successful.
     *
     * IMPORTANT: If the token implements ERC-7674 (ERC-20 with temporary allowance), and if the "client"
     * smart contract uses ERC-7674 to set temporary allowances, then the "client" smart contract should avoid using
     * this function. Performing a {safeIncreaseAllowance} or {safeDecreaseAllowance} operation on a token contract
     * that has a non-zero temporary allowance (for that particular owner-spender) will result in unexpected behavior.
     */
    function safeDecreaseAllowance(IERC20 token, address spender, uint256 requestedDecrease) internal {
        unchecked {
            uint256 currentAllowance = token.allowance(address(this), spender);
            if (currentAllowance < requestedDecrease) {
                revert SafeERC20FailedDecreaseAllowance(spender, currentAllowance, requestedDecrease);
            }
            forceApprove(token, spender, currentAllowance - requestedDecrease);
        }
    }

    /**
     * @dev Set the calling contract's allowance toward `spender` to `value`. If `token` returns no value,
     * non-reverting calls are assumed to be successful. Meant to be used with tokens that require the approval
     * to be set to zero before setting it to a non-zero value, such as USDT.
     *
     * NOTE: If the token implements ERC-7674, this function will not modify any temporary allowance. This function
     * only sets the "standard" allowance. Any temporary allowance will remain active, in addition to the value being
     * set here.
     */
    function forceApprove(IERC20 token, address spender, uint256 value) internal {
        bytes memory approvalCall = abi.encodeCall(token.approve, (spender, value));

        if (!_callOptionalReturnBool(token, approvalCall)) {
            _callOptionalReturn(token, abi.encodeCall(token.approve, (spender, 0)));
            _callOptionalReturn(token, approvalCall);
        }
    }

    /**
     * @dev Performs an {ERC1363} transferAndCall, with a fallback to the simple {ERC20} transfer if the target has no
     * code. This can be used to implement an {ERC721}-like safe transfer that rely on {ERC1363} checks when
     * targeting contracts.
     *
     * Reverts if the returned value is other than `true`.
     */
    function transferAndCallRelaxed(IERC1363 token, address to, uint256 value, bytes memory data) internal {
        if (to.code.length == 0) {
            safeTransfer(token, to, value);
        } else if (!token.transferAndCall(to, value, data)) {
            revert SafeERC20FailedOperation(address(token));
        }
    }

    /**
     * @dev Performs an {ERC1363} transferFromAndCall, with a fallback to the simple {ERC20} transferFrom if the target
     * has no code. This can be used to implement an {ERC721}-like safe transfer that rely on {ERC1363} checks when
     * targeting contracts.
     *
     * Reverts if the returned value is other than `true`.
     */
    function transferFromAndCallRelaxed(
        IERC1363 token,
        address from,
        address to,
        uint256 value,
        bytes memory data
    ) internal {
        if (to.code.length == 0) {
            safeTransferFrom(token, from, to, value);
        } else if (!token.transferFromAndCall(from, to, value, data)) {
            revert SafeERC20FailedOperation(address(token));
        }
    }

    /**
     * @dev Performs an {ERC1363} approveAndCall, with a fallback to the simple {ERC20} approve if the target has no
     * code. This can be used to implement an {ERC721}-like safe transfer that rely on {ERC1363} checks when
     * targeting contracts.
     *
     * NOTE: When the recipient address (`to`) has no code (i.e. is an EOA), this function behaves as {forceApprove}.
     * Opposedly, when the recipient address (`to`) has code, this function only attempts to call {ERC1363-approveAndCall}
     * once without retrying, and relies on the returned value to be true.
     *
     * Reverts if the returned value is other than `true`.
     */
    function approveAndCallRelaxed(IERC1363 token, address to, uint256 value, bytes memory data) internal {
        if (to.code.length == 0) {
            forceApprove(token, to, value);
        } else if (!token.approveAndCall(to, value, data)) {
            revert SafeERC20FailedOperation(address(token));
        }
    }

    /**
     * @dev Imitates a Solidity high-level call (i.e. a regular function call to a contract), relaxing the requirement
     * on the return value: the return value is optional (but if data is returned, it must not be false).
     * @param token The token targeted by the call.
     * @param data The call data (encoded using abi.encode or one of its variants).
     *
     * This is a variant of {_callOptionalReturnBool} that reverts if call fails to meet the requirements.
     */
    function _callOptionalReturn(IERC20 token, bytes memory data) private {
        uint256 returnSize;
        uint256 returnValue;
        assembly ("memory-safe") {
            let success := call(gas(), token, 0, add(data, 0x20), mload(data), 0, 0x20)
            // bubble errors
            if iszero(success) {
                let ptr := mload(0x40)
                returndatacopy(ptr, 0, returndatasize())
                revert(ptr, returndatasize())
            }
            returnSize := returndatasize()
            returnValue := mload(0)
        }

        if (returnSize == 0 ? address(token).code.length == 0 : returnValue != 1) {
            revert SafeERC20FailedOperation(address(token));
        }
    }

    /**
     * @dev Imitates a Solidity high-level call (i.e. a regular function call to a contract), relaxing the requirement
     * on the return value: the return value is optional (but if data is returned, it must not be false).
     * @param token The token targeted by the call.
     * @param data The call data (encoded using abi.encode or one of its variants).
     *
     * This is a variant of {_callOptionalReturn} that silently catches all reverts and returns a bool instead.
     */
    function _callOptionalReturnBool(IERC20 token, bytes memory data) private returns (bool) {
        bool success;
        uint256 returnSize;
        uint256 returnValue;
        assembly ("memory-safe") {
            success := call(gas(), token, 0, add(data, 0x20), mload(data), 0, 0x20)
            returnSize := returndatasize()
            returnValue := mload(0)
        }
        return success && (returnSize == 0 ? address(token).code.length > 0 : returnValue == 1);
    }
}

// contracts/Agreement.sol

interface IInternetCourtFactory {
    function requestDispute(address agreementAddress) external;
}

/**
 * @title Agreement
 * @notice Individual agreement contract deployed per case. Manages USDC escrow, state machine,
 *         evidence submission, mutual agreement path, and bridge-delivered verdicts.
 *
 * State machine: CREATED -> ACTIVE -> DISPUTED -> RESOLVING -> RESOLVED / CANCELLED
 *
 * Escrow is held in USDC (ERC-20). Party A deposits escrow at creation (via factory).
 * Party B joins free (no deposit required).
 *
 * Two resolution paths:
 *   1. Mutual agreement (2-of-2): Both parties propose the same outcome -> resolves without jury
 *   2. Dispute path: Evidence submitted -> AI jury evaluates -> verdict delivered via bridge
 */
contract Agreement is IResolutionTarget {
    using SafeERC20 for IERC20;

    // ──────────────────────────────────────────────
    //  Enums
    // ──────────────────────────────────────────────

    enum Status { CREATED, ACTIVE, DISPUTED, RESOLVING, RESOLVED, CANCELLED }
    enum Verdict { UNDETERMINED, TRUE_, FALSE_ }

    // ──────────────────────────────────────────────
    //  State variables
    // ──────────────────────────────────────────────

    // Parties
    address public partyA;
    address public partyB;

    // Contract terms
    string public statement;
    string public guidelines;
    string public evidenceDefs;

    // Evidence
    string public evidenceA;
    string public evidenceB;
    bool public evidenceASubmitted;
    bool public evidenceBSubmitted;

    // Evidence deadline
    uint256 public evidenceDeadlineSeconds;
    uint256 public disputeTimestamp;

    // Grace period for deadline=0 cases
    uint256 public constant DEFAULT_GRACE_PERIOD = 7 days;

    // Inactivity timeout for ACTIVE state
    uint256 public activatedTimestamp;
    uint256 public constant INACTIVITY_TIMEOUT = 90 days;

    // Escrow (USDC)
    IERC20 public usdcToken;
    uint256 public escrowAmount;

    // Join deadline
    uint256 public joinDeadline;

    // Dispute initiator (for default judgment)
    address public disputeInitiator;

    // Evidence constraints
    uint256 public maxEvidenceLength;
    string public constraints;

    // Factory reference (for bridge callback)
    address public factory;

    // Status & resolution
    Status public status;
    Verdict public verdict;
    string public reasoning;

    // Mutual agreement path
    // 0 = no proposal, 1 = TRUE proposed, 2 = FALSE proposed
    uint8 public proposalA;
    uint8 public proposalB;

    // Pull-based withdrawal pattern: pending amounts per party
    mapping(address => uint256) public pendingWithdrawals;

    // ──────────────────────────────────────────────
    //  Events
    // ──────────────────────────────────────────────

    event AgreementAccepted(address indexed partyB, uint256 escrowAmount);
    event OutcomeProposed(address indexed proposer, bool statementIsTrue);
    event OutcomeConfirmed(Verdict verdict);
    event DisputeRaised(address indexed raisedBy, uint256 evidenceDeadline);
    event EvidenceSubmitted(address indexed submitter);
    event ResolutionTriggered(uint256 timestamp);
    event Resolved(Verdict verdict, string reasoning);
    event FundsClaimed(address indexed claimant, uint256 amount);
    event Cancelled(address indexed cancelledBy);
    event AutoDisputed(address indexed secondProposer);

    // ──────────────────────────────────────────────
    //  Modifiers
    // ──────────────────────────────────────────────

    modifier onlyPartyA() {
        require(msg.sender == partyA, "Only party A");
        _;
    }

    modifier onlyPartyB() {
        require(msg.sender == partyB, "Only party B");
        _;
    }

    modifier onlyParty() {
        require(msg.sender == partyA || msg.sender == partyB, "Only a party");
        _;
    }

    modifier onlyFactory() {
        require(msg.sender == factory, "Only factory");
        _;
    }

    modifier inStatus(Status _status) {
        require(status == _status, "Wrong status");
        _;
    }

    // ──────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────

    /**
     * @notice Deploy a new agreement. The factory handles USDC transfer before deployment.
     * @param _partyA Address of party A (the creator)
     * @param _partyB Address of party B (the counterparty)
     * @param _statement The claim to be evaluated as true/false
     * @param _guidelines Instructions for how the AI jury should evaluate the statement
     * @param _evidenceDefs What types of evidence each side can submit
     * @param _evidenceDeadlineSeconds Seconds after dispute for evidence submission window
     * @param _factory Address of the InternetCourtFactory contract
     * @param _usdcToken Address of the USDC token contract
     * @param _escrowAmount Amount of USDC escrowed by party A
     * @param _joinDeadline Timestamp by which party B must accept (0 = no deadline)
     * @param _maxEvidenceLength Maximum length of evidence in bytes (0 = no limit)
     * @param _constraints Additional constraints string
     */
    constructor(
        address _partyA,
        address _partyB,
        string memory _statement,
        string memory _guidelines,
        string memory _evidenceDefs,
        uint256 _evidenceDeadlineSeconds,
        address _factory,
        address _usdcToken,
        uint256 _escrowAmount,
        uint256 _joinDeadline,
        uint256 _maxEvidenceLength,
        string memory _constraints
    ) {
        require(_partyA != address(0), "Invalid party A");
        require(_partyB != address(0), "Invalid party B");
        require(_partyA != _partyB, "Parties must differ");
        require(_factory != address(0), "Invalid factory");
        require(bytes(_statement).length > 0, "Empty statement");
        if (_escrowAmount > 0) {
            require(_usdcToken != address(0), "USDC token required for escrow");
        }
        if (_joinDeadline > 0) {
            require(_joinDeadline > block.timestamp, "Join deadline must be in the future");
        }

        partyA = _partyA;
        partyB = _partyB;
        statement = _statement;
        guidelines = _guidelines;
        evidenceDefs = _evidenceDefs;
        evidenceDeadlineSeconds = _evidenceDeadlineSeconds;
        factory = _factory;
        usdcToken = IERC20(_usdcToken);
        escrowAmount = _escrowAmount;
        joinDeadline = _joinDeadline;
        maxEvidenceLength = _maxEvidenceLength;
        constraints = _constraints;
        status = Status.CREATED;
    }

    // ──────────────────────────────────────────────
    //  Party B: Accept agreement
    // ──────────────────────────────────────────────

    /**
     * @notice Party B accepts the agreement. No deposit required.
     */
    function acceptAgreement() external onlyPartyB inStatus(Status.CREATED) {
        if (joinDeadline > 0) {
            require(block.timestamp <= joinDeadline, "Join deadline passed");
        }

        status = Status.ACTIVE;
        activatedTimestamp = block.timestamp;

        emit AgreementAccepted(partyB, escrowAmount);
    }

    // ──────────────────────────────────────────────
    //  Reclaim on expiry
    // ──────────────────────────────────────────────

    /**
     * @notice Reclaim escrowed USDC after the join deadline has expired without party B accepting.
     *         Anyone can call this to trigger the reclaim.
     */
    function reclaimOnExpiry() external inStatus(Status.CREATED) {
        require(joinDeadline > 0, "No join deadline set");
        require(block.timestamp > joinDeadline, "Deadline not passed");

        status = Status.CANCELLED;

        emit Cancelled(partyA);

        if (escrowAmount > 0 && address(usdcToken) != address(0)) {
            uint256 amount = escrowAmount;
            escrowAmount = 0;
            usdcToken.safeTransfer(partyA, amount);
        }
    }

    // ──────────────────────────────────────────────
    //  Mutual agreement path (2-of-2)
    // ──────────────────────────────────────────────

    /**
     * @notice Propose an outcome. If both parties propose the same outcome, the agreement resolves.
     * @param statementIsTrue true = statement is TRUE, false = statement is FALSE
     */
    function proposeOutcome(bool statementIsTrue) external onlyParty inStatus(Status.ACTIVE) {
        uint8 proposal = statementIsTrue ? 1 : 2;

        if (msg.sender == partyA) {
            proposalA = proposal;
        } else {
            proposalB = proposal;
        }

        emit OutcomeProposed(msg.sender, statementIsTrue);

        // Check if both parties have proposed the same outcome
        if (proposalA != 0 && proposalA == proposalB) {
            verdict = proposalA == 1 ? Verdict.TRUE_ : Verdict.FALSE_;
            status = Status.RESOLVED;
            reasoning = "Resolved by mutual agreement";

            emit OutcomeConfirmed(verdict);
            emit Resolved(verdict, reasoning);

            _releaseEscrow();
        }
        // Auto-dispute if both proposed but differ
        else if (proposalA != 0 && proposalB != 0 && proposalA != proposalB) {
            status = Status.DISPUTED;
            disputeTimestamp = block.timestamp;
            disputeInitiator = msg.sender;

            uint256 deadline = block.timestamp + evidenceDeadlineSeconds;
            emit AutoDisputed(msg.sender);
            emit DisputeRaised(msg.sender, deadline);
        }
    }

    /**
     * @notice Confirm the other party's proposed outcome. Shorthand for proposing the same outcome.
     *         Only callable if the other party has already proposed.
     */
    function confirmOutcome() external onlyParty inStatus(Status.ACTIVE) {
        uint8 otherProposal;

        if (msg.sender == partyA) {
            otherProposal = proposalB;
            require(otherProposal != 0, "No proposal to confirm");
            proposalA = otherProposal;
        } else {
            otherProposal = proposalA;
            require(otherProposal != 0, "No proposal to confirm");
            proposalB = otherProposal;
        }

        verdict = otherProposal == 1 ? Verdict.TRUE_ : Verdict.FALSE_;
        status = Status.RESOLVED;
        reasoning = "Resolved by mutual agreement";

        emit OutcomeConfirmed(verdict);
        emit Resolved(verdict, reasoning);

        _releaseEscrow();
    }

    // ──────────────────────────────────────────────
    //  Dispute path
    // ──────────────────────────────────────────────

    /**
     * @notice Raise a dispute. Opens the evidence submission window.
     *         Can be called by either party when the agreement is ACTIVE.
     */
    function raiseDispute() external onlyParty inStatus(Status.ACTIVE) {
        status = Status.DISPUTED;
        disputeTimestamp = block.timestamp;
        disputeInitiator = msg.sender;

        uint256 deadline = block.timestamp + evidenceDeadlineSeconds;
        emit DisputeRaised(msg.sender, deadline);
    }

    /**
     * @notice Submit evidence. Each party can submit once during the evidence window.
     * @param evidence The evidence string (content depends on evidenceDefs)
     */
    function submitEvidence(string calldata evidence) external onlyParty inStatus(Status.DISPUTED) {
        require(bytes(evidence).length > 0, "Empty evidence");

        if (maxEvidenceLength > 0) {
            require(bytes(evidence).length <= maxEvidenceLength, "Evidence exceeds max length");
        }

        // Check evidence deadline
        if (evidenceDeadlineSeconds > 0) {
            require(
                block.timestamp <= disputeTimestamp + evidenceDeadlineSeconds,
                "Evidence deadline passed"
            );
        }

        if (msg.sender == partyA) {
            require(!evidenceASubmitted, "Already submitted");
            evidenceA = evidence;
            evidenceASubmitted = true;
        } else {
            require(!evidenceBSubmitted, "Already submitted");
            evidenceB = evidence;
            evidenceBSubmitted = true;
        }

        emit EvidenceSubmitted(msg.sender);

        // If both parties have submitted, trigger resolution
        if (evidenceASubmitted && evidenceBSubmitted) {
            _triggerResolution();
        }
    }

    /**
     * @notice Close the evidence window and trigger resolution after the deadline.
     *         Anyone can call this once the evidence deadline has passed.
     */
    function closeEvidenceWindow() external inStatus(Status.DISPUTED) {
        uint256 effectiveDeadline = evidenceDeadlineSeconds > 0
            ? evidenceDeadlineSeconds
            : DEFAULT_GRACE_PERIOD;
        require(
            block.timestamp > disputeTimestamp + effectiveDeadline,
            "Deadline not passed"
        );
        require(evidenceASubmitted && evidenceBSubmitted, "Use resolveByDefault for partial/no evidence");

        _triggerResolution();
    }

    // ──────────────────────────────────────────────
    //  Default judgment
    // ──────────────────────────────────────────────

    /**
     * @notice Resolve by default judgment after evidence deadline passes.
     *         Neither party submitted → UNDETERMINED; only initiator submitted → initiator wins;
     *         only non-initiator submitted → non-initiator wins.
     */
    function resolveByDefault() external inStatus(Status.DISPUTED) {
        uint256 effectiveDeadline = evidenceDeadlineSeconds > 0
            ? evidenceDeadlineSeconds
            : DEFAULT_GRACE_PERIOD;
        require(block.timestamp > disputeTimestamp + effectiveDeadline, "Deadline not passed");
        require(!(evidenceASubmitted && evidenceBSubmitted), "Both parties submitted evidence");
        require(disputeInitiator != address(0), "No dispute initiator");

        if (!evidenceASubmitted && !evidenceBSubmitted) {
            verdict = (disputeInitiator == partyA) ? Verdict.TRUE_ : Verdict.FALSE_;
            reasoning = "Resolved by default - no evidence submitted, dispute initiator wins";
        } else {
            address nonInitiator = disputeInitiator == partyA ? partyB : partyA;
            bool initiatorSubmitted = (disputeInitiator == partyA) ? evidenceASubmitted : evidenceBSubmitted;
            bool nonInitiatorSubmitted = (nonInitiator == partyA) ? evidenceASubmitted : evidenceBSubmitted;

            if (initiatorSubmitted && !nonInitiatorSubmitted) {
                verdict = (disputeInitiator == partyA) ? Verdict.TRUE_ : Verdict.FALSE_;
                reasoning = "Resolved by default - only dispute initiator submitted evidence";
            } else {
                verdict = (nonInitiator == partyA) ? Verdict.TRUE_ : Verdict.FALSE_;
                reasoning = "Resolved by default - only non-initiator submitted evidence";
            }
        }

        status = Status.RESOLVED;

        emit Resolved(verdict, reasoning);

        _releaseEscrow();
    }

    // ──────────────────────────────────────────────
    //  Bridge verdict (factory-only)
    // ──────────────────────────────────────────────

    /**
     * @notice Set the resolution verdict. Only callable by the factory (via bridge).
     * @param _verdict The verdict: 0 = UNDETERMINED, 1 = TRUE, 2 = FALSE
     * @param _reasoning The AI jury's reasoning
     */
    function setResolution(uint8 _verdict, string calldata _reasoning) external onlyFactory {
        require(status == Status.RESOLVING, "Not in resolving state");
        require(_verdict <= 2, "Invalid verdict");

        verdict = Verdict(_verdict);
        reasoning = _reasoning;
        status = Status.RESOLVED;

        emit Resolved(verdict, reasoning);

        _releaseEscrow();
    }

    // ──────────────────────────────────────────────
    //  Cancel (before acceptance)
    // ──────────────────────────────────────────────

    /**
     * @notice Cancel the agreement before party B has accepted.
     *         Returns party A's USDC escrow deposit.
     */
    function cancel() external onlyPartyA inStatus(Status.CREATED) {
        status = Status.CANCELLED;

        emit Cancelled(msg.sender);

        if (escrowAmount > 0 && address(usdcToken) != address(0)) {
            uint256 amount = escrowAmount;
            escrowAmount = 0;
            usdcToken.safeTransfer(partyA, amount);
        }
    }

    // ──────────────────────────────────────────────
    //  Inactivity escape (ACTIVE state)
    // ──────────────────────────────────────────────

    /**
     * @notice Cancel an ACTIVE agreement that has been inactive for INACTIVITY_TIMEOUT.
     *         Returns escrow to party A. Anyone can call.
     */
    function cancelInactive() external inStatus(Status.ACTIVE) {
        require(activatedTimestamp > 0, "Not activated");
        require(
            block.timestamp > activatedTimestamp + INACTIVITY_TIMEOUT,
            "Inactivity timeout not reached"
        );

        status = Status.CANCELLED;

        emit Cancelled(address(0));

        if (escrowAmount > 0 && address(usdcToken) != address(0)) {
            uint256 amount = escrowAmount;
            escrowAmount = 0;
            usdcToken.safeTransfer(partyA, amount);
        }
    }

    // ──────────────────────────────────────────────
    //  View methods (for relay service)
    // ──────────────────────────────────────────────

    function getStatement() external view returns (string memory) {
        return statement;
    }

    function getGuidelines() external view returns (string memory) {
        return guidelines;
    }

    function getEvidenceDefs() external view returns (string memory) {
        return evidenceDefs;
    }

    function getEvidenceA() external view returns (string memory) {
        return evidenceA;
    }

    function getEvidenceB() external view returns (string memory) {
        return evidenceB;
    }

    function getPartyA() external view returns (address) {
        return partyA;
    }

    function getPartyB() external view returns (address) {
        return partyB;
    }

    function getEvidenceDeadline() external view returns (uint256) {
        if (disputeTimestamp == 0) return 0;
        return disputeTimestamp + evidenceDeadlineSeconds;
    }

    function getTotalEscrow() external view returns (uint256) {
        return escrowAmount;
    }

    // ── IResolutionTarget: oracle dispatch ────────────────────────────────────

    /// @notice Oracle type for agent disputes. Relay deploys case_resolution.py.
    bytes32 public constant ORACLE_TYPE = keccak256("AGENT_DISPUTE_V1");

    function getOracleType() external pure override returns (bytes32) {
        return ORACLE_TYPE;
    }

    /**
     * @notice Returns ABI-encoded constructor args for case_resolution.py:
     *         (agreement_address, statement, guidelines, evidence_a, evidence_b,
     *          evidence_defs, bridge_sender, target_chain_eid, target_contract)
     *
     *         bridge_sender and target_chain_eid are injected by the relay from
     *         its own config; they are not stored on-chain. The relay appends them
     *         after decoding this payload. Encoded here: address + 6 strings.
     */
    function getOracleArgs() external view override returns (bytes memory) {
        return abi.encode(
            address(this), // agreement_address
            statement,
            guidelines,
            evidenceA,
            evidenceB,
            evidenceDefs
        );
    }

    // ──────────────────────────────────────────────
    //  Internal functions
    // ──────────────────────────────────────────────

    /**
     * @dev Transition to RESOLVING state and notify the factory to emit DisputeRequested.
     */
    function _triggerResolution() internal {
        status = Status.RESOLVING;

        emit ResolutionTriggered(block.timestamp);

        // Notify the factory to emit DisputeRequested for the relay service
        IInternetCourtFactory(factory).requestDispute(address(this));
    }

    /**
     * @dev Calculate and store pending withdrawal amounts based on the verdict.
     *      TRUE  -> all escrow to party A
     *      FALSE -> all escrow to party B
     *      UNDETERMINED -> refund to party A (creator)
     */
    function _releaseEscrow() internal {
        if (escrowAmount == 0 || address(usdcToken) == address(0)) return;

        uint256 amount = escrowAmount;
        escrowAmount = 0;

        if (verdict == Verdict.TRUE_) {
            pendingWithdrawals[partyA] += amount;
        } else if (verdict == Verdict.FALSE_) {
            pendingWithdrawals[partyB] += amount;
        } else {
            // UNDETERMINED: refund to creator
            pendingWithdrawals[partyA] += amount;
        }
    }

    /**
     * @notice Withdraw pending USDC funds after resolution. Pull-based pattern prevents
     *         a reverting recipient from blocking the other party's withdrawal.
     */
    function claimFunds() external {
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "Nothing to claim");

        pendingWithdrawals[msg.sender] = 0;

        require(address(usdcToken) != address(0), "No USDC token set");
        usdcToken.safeTransfer(msg.sender, amount);

        emit FundsClaimed(msg.sender, amount);
    }
}

// contracts/InternetCourtFactory.sol

/**
 * @title InternetCourtFactory
 * @notice Universal registry and verdict router for InternetCourt cases.
 *
 *         Two registration paths:
 *           1. createAgreement() — factory deploys an Agreement contract (agent disputes)
 *           2. registerCase()    — external contract self-registers (trade finance, etc.)
 *
 *         All registered cases implement IResolutionTarget. The factory routes
 *         bridge verdicts to IResolutionTarget(caseAddr).setResolution(verdict, reasoning).
 *         Each case type handles its own escrow and settlement logic internally.
 *
 *         The relay reads IResolutionTarget.getOracleType() and getOracleArgs() to
 *         dispatch the correct GenLayer oracle without any case-type logic in the relay.
 */
contract InternetCourtFactory is IGenLayerBridgeReceiver, Ownable {
    using SafeERC20 for IERC20;

    // ──────────────────────────────────────────────
    //  State
    // ──────────────────────────────────────────────

    /// @notice Address of the BridgeReceiver. Only it may deliver verdicts.
    address public bridgeReceiver;

    /// @notice Auto-incrementing case ID counter.
    uint256 public nextAgreementId;

    /// @notice Registered case address → registered flag.
    ///         Covers both factory-deployed Agreement contracts and self-registered externals.
    mapping(address => bool) public deployedAgreements;

    /// @notice Case ID → case address.
    mapping(uint256 => address) public agreements;

    /// @notice Case address → case ID (reverse lookup).
    mapping(address => uint256) public agreementIds;

    /// @notice Block at deployment (for efficient event indexing).
    uint256 public immutable deploymentBlock;

    // ──────────────────────────────────────────────
    //  Events
    // ──────────────────────────────────────────────

    event AgreementCreated(
        uint256 indexed id,
        address agreementAddress,
        address partyA,
        address partyB
    );

    /// @notice Emitted when any registered case enters dispute resolution.
    ///         The relay watches this event and uses IResolutionTarget.getOracleType()
    ///         + getOracleArgs() to dispatch the correct oracle.
    event DisputeRequested(
        address indexed agreementAddress,
        uint256 timestamp
    );

    event VerdictReceived(
        address indexed agreementAddress,
        uint8 verdict
    );

    /// @notice Emitted when an external contract self-registers as a case.
    event CaseRegistered(
        uint256 indexed id,
        address indexed caseAddress
    );

    // ──────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────

    constructor(address _bridgeReceiver, address _owner) Ownable(_owner) {
        deploymentBlock = block.number;
        bridgeReceiver = _bridgeReceiver;
    }

    // ──────────────────────────────────────────────
    //  Agreement creation (agent disputes)
    // ──────────────────────────────────────────────

    /**
     * @notice Deploy a new Agreement contract for an agent-to-agent (or agent-to-human) dispute.
     *         Party A deposits USDC escrow; escrow is forwarded to the Agreement.
     */
    function createAgreement(
        address partyB,
        string calldata _statement,
        string calldata _guidelines,
        string calldata _evidenceDefs,
        uint256 _evidenceDeadlineSeconds,
        address _usdcToken,
        uint256 _escrowAmount,
        uint256 _joinDeadline,
        uint256 _maxEvidenceLength,
        string calldata _constraints
    ) external returns (address) {
        if (_escrowAmount > 0) {
            require(_usdcToken != address(0), "USDC token required for escrow");
            IERC20(_usdcToken).safeTransferFrom(msg.sender, address(this), _escrowAmount);
        }

        Agreement agreement = new Agreement(
            msg.sender,
            partyB,
            _statement,
            _guidelines,
            _evidenceDefs,
            _evidenceDeadlineSeconds,
            address(this),
            _usdcToken,
            _escrowAmount,
            _joinDeadline,
            _maxEvidenceLength,
            _constraints
        );

        if (_escrowAmount > 0) {
            IERC20(_usdcToken).safeTransfer(address(agreement), _escrowAmount);
        }

        uint256 id = _register(address(agreement));
        emit AgreementCreated(id, address(agreement), msg.sender, partyB);
        return address(agreement);
    }

    // ──────────────────────────────────────────────
    //  External case registration (trade finance, etc.)
    // ──────────────────────────────────────────────

    /**
     * @notice Called by an external contract to register itself as a case and
     *         trigger dispute resolution. The caller must implement IResolutionTarget.
     *
     *         The relay will pick up the DisputeRequested event, call
     *         getOracleType() + getOracleArgs() on msg.sender, and deploy the
     *         appropriate GenLayer oracle automatically.
     *
     * @return id  The assigned case ID.
     */
    function registerCase() external returns (uint256 id) {
        id = _register(msg.sender);
        emit CaseRegistered(id, msg.sender);
        emit DisputeRequested(msg.sender, block.timestamp);
    }

    // ──────────────────────────────────────────────
    //  Dispute request (called by Agreement contracts)
    // ──────────────────────────────────────────────

    /**
     * @notice Called by an Agreement contract when it enters RESOLVING state.
     *         Emits DisputeRequested for the relay to pick up.
     */
    function requestDispute(address agreementAddress) external {
        require(deployedAgreements[agreementAddress], "Unknown case");
        require(msg.sender == agreementAddress, "Only case can request");
        emit DisputeRequested(agreementAddress, block.timestamp);
    }

    // ──────────────────────────────────────────────
    //  Bridge verdict delivery
    // ──────────────────────────────────────────────

    /**
     * @notice Receive and route a verdict from GenLayer via the bridge.
     *         Called by BridgeReceiver after LayerZero delivers the message.
     *
     * @param message ABI-encoded:
     *   (address caseAddress, bytes resolutionData)
     *   where resolutionData = ABI-encoded (address _ignored, uint8 verdict, string reasoning)
     *
     *   Routes to IResolutionTarget(caseAddress).setResolution(verdict, reasoning).
     *   The case contract handles its own escrow settlement.
     */
    function processBridgeMessage(
        uint32 /* srcChainId */,
        address /* srcSender */,
        bytes calldata message
    ) external override {
        require(msg.sender == bridgeReceiver, "Only bridge receiver");

        (address caseAddress, bytes memory resolutionData) =
            abi.decode(message, (address, bytes));

        require(deployedAgreements[caseAddress], "Unknown case");

        (, uint8 _verdict, string memory _reasoning) =
            abi.decode(resolutionData, (address, uint8, string));

        // Generic: works for Agreement, TradeFxSettlement, or any future IResolutionTarget
        IResolutionTarget(caseAddress).setResolution(_verdict, _reasoning);

        emit VerdictReceived(caseAddress, _verdict);
    }

    // ──────────────────────────────────────────────
    //  Admin
    // ──────────────────────────────────────────────

    function setBridgeReceiver(address _bridgeReceiver) external onlyOwner {
        bridgeReceiver = _bridgeReceiver;
    }

    // ──────────────────────────────────────────────
    //  Internal
    // ──────────────────────────────────────────────

    function _register(address caseAddr) internal returns (uint256 id) {
        require(!deployedAgreements[caseAddr], "Already registered");
        id = nextAgreementId++;
        deployedAgreements[caseAddr] = true;
        agreements[id] = caseAddr;
        agreementIds[caseAddr] = id;
    }
}

